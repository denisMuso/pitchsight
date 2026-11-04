import shutil
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.db import Incident, Job, Match, Prediction, Review, VideoAsset
from pitchsight.jobs.runner import QueueFull
from pitchsight.video.processing import (
    EXTENSIONS,
    MAX_BYTES,
    browser_copy,
    process_video,
    validate_header,
)


class IncidentInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    match_id: str | None = None


class ReviewInput(BaseModel):
    decision: Literal["FOUL", "NO FOUL", "INCONCLUSIVE"]
    comments: str = Field(default="", max_length=4000)


def routes(app, root: Path):
    router = APIRouter(prefix="/api")
    factory = app.state.factory
    validation_slots = BoundedSemaphore(2)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    def require_incident(session, iid):
        incident = session.get(Incident, iid)
        if not incident:
            raise HTTPException(404, "Incident not found")
        return incident

    @router.post("/incidents", status_code=201)
    def create_incident(body: IncidentInput):
        with factory.begin() as session:
            if body.match_id and not session.get(Match, body.match_id):
                raise HTTPException(404, "Match not found")
            row = Incident(id=uuid4().hex, title=body.title, match_id=body.match_id)
            session.add(row)
        return {"id": row.id, "title": row.title}

    @router.get("/incidents")
    def list_incidents():
        with factory() as session:
            return {
                "items": session.scalars(
                    select(Incident).order_by(Incident.created_at.desc()).limit(100)
                ).all()
            }

    @router.get("/incidents/{iid}")
    def get_incident(iid: str):
        with factory() as session:
            incident = require_incident(session, iid)
            assets = session.scalars(select(VideoAsset).where(VideoAsset.incident_id == iid)).all()
            return {
                "incident": incident,
                "views": [
                    {
                        "id": a.id,
                        "view_name": a.view_name,
                        "metadata": a.metadata_json,
                        "url": f"/api/videos/{a.id}",
                        "thumbnail": f"/api/videos/{a.id}/thumbnail",
                    }
                    for a in assets
                ],
                "jobs": session.scalars(
                    select(Job).where(Job.incident_id == iid).order_by(Job.created_at.desc())
                ).all(),
                "reviews": session.scalars(
                    select(Review).where(Review.incident_id == iid).order_by(Review.id.desc())
                ).all(),
                "predictions": session.scalars(
                    select(Prediction)
                    .where(Prediction.incident_id == iid)
                    .order_by(Prediction.id.desc())
                ).all(),
            }

    @router.post("/incidents/{iid}/videos", status_code=202)
    def upload(
        iid: str,
        file: UploadFile = File(...),
        view_name: str = Form(..., min_length=1, max_length=80),
        authorized: bool = Form(False),
    ):
        if not authorized:
            raise HTTPException(400, "Confirm you are authorized to process this clip")
        with factory() as session:
            require_incident(session, iid)
            if session.scalar(
                select(VideoAsset).where(
                    VideoAsset.incident_id == iid, VideoAsset.view_name == view_name
                )
            ):
                raise HTTPException(409, "View name already exists in this incident")
        ext = Path(file.filename or "").suffix.lower()
        if ext not in EXTENSIONS:
            raise HTTPException(415, "Allowed formats: MP4, MOV, AVI, WebM")
        aid = uuid4().hex
        folder = root / aid
        folder.mkdir()
        path = folder / f"source{ext}"
        try:
            size = 0
            with path.open("wb") as output:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(413, "Video exceeds 100 MiB")
                    output.write(chunk)
            validate_header(path)
            # Validate before accepting the asset; hard subprocess timeout protects API worker.
            if not validation_slots.acquire(blocking=False):
                raise HTTPException(429, "Video validation busy; retry later")
            try:
                metadata = process_video(path, folder)
            finally:
                validation_slots.release()
            with factory.begin() as session:
                session.add(
                    VideoAsset(
                        id=aid,
                        incident_id=iid,
                        view_name=view_name,
                        path=str(path),
                        metadata_json=metadata,
                    )
                )

            def process(progress):
                progress(35)
                browser_copy(path, folder / "playback.mp4")
                progress(90)

            try:
                jid = app.state.runner.submit(iid, "video", process)
            except QueueFull:
                with factory.begin() as session:
                    session.delete(session.get(VideoAsset, aid))
                raise HTTPException(429, "Local queue full; retry later") from None
            return {"asset_id": aid, "job_id": jid}
        except HTTPException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        except (ValueError, IntegrityError) as exc:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(
                422, str(exc) if isinstance(exc, ValueError) else "Duplicate view"
            ) from None
        finally:
            file.file.close()

    @router.get("/videos/{aid}")
    def video(aid: str):
        with factory() as session:
            asset = session.get(VideoAsset, aid)
            if not asset:
                raise HTTPException(404, "Video not found")
            path = Path(asset.path).parent / "playback.mp4"
            if not path.is_file():
                raise HTTPException(409, "Playback conversion not complete; inspect job state")
            return FileResponse(path, media_type="video/mp4")

    @router.get("/videos/{aid}/thumbnail")
    def thumbnail(aid: str):
        with factory() as session:
            asset = session.get(VideoAsset, aid)
            if not asset:
                raise HTTPException(404, "Video not found")
            return FileResponse(Path(asset.path).parent / "thumbnail.jpg", media_type="image/jpeg")

    @router.post("/incidents/{iid}/reviews", status_code=201)
    def review(iid: str, body: ReviewInput):
        with factory.begin() as session:
            require_incident(session, iid)
            row = Review(incident_id=iid, decision=body.decision, comments=body.comments)
            session.add(row)
        return {"id": row.id, "decision": row.decision, "created_at": row.created_at}

    @router.get("/jobs/{jid}")
    def job(jid: str):
        with factory() as session:
            row = session.get(Job, jid)
            if not row:
                raise HTTPException(404, "Job not found")
            return row

    app.include_router(router)
