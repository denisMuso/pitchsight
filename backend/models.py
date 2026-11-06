import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.db import Incident, Prediction, VideoAsset
from pitchsight.inference.registry import ModelUnavailable, active_manifest, predict
from pitchsight.jobs.runner import QueueFull


def routes(app):
    router = APIRouter(prefix="/api")
    factory = app.state.factory

    @router.get("/training/preflight")
    def training_preflight():
        path = Path("artifacts/preflight.json")
        if not path.is_file():
            return {"status": "not checked", "checks": [], "dataset": None}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise HTTPException(
                503, "Preflight report unreadable; rerun the preflight CLI"
            ) from None

    @router.get("/models")
    def models():
        try:
            manifest, _ = active_manifest()
            return {"status": "AVAILABLE", "model": manifest.model_dump()}
        except ModelUnavailable as exc:
            return {"status": "MODEL UNAVAILABLE", "detail": str(exc), "model": None}

    @router.get("/experiments")
    def experiments():
        results = []
        for path in sorted(Path("artifacts/runs").glob("*/metrics.json"), reverse=True)[:50]:
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
                audit_path = path.parent / "evaluation-audit.json"
                if audit_path.is_file():
                    audit = json.loads(audit_path.read_text(encoding="utf-8"))
                    result["audit"] = {
                        split: {
                            "selective": value["selective"],
                            "paired_comparison": value["paired_comparison"],
                        }
                        for split, value in audit["splits"].items()
                    }
                results.append(result)
            except (OSError, ValueError):
                continue
        return {"items": results}

    @router.get("/training/progress")
    def training_progress():
        results = []
        for path in sorted(Path("artifacts/runs").glob("*/progress.json"), reverse=True)[:50]:
            try:
                results.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return {"items": results}

    @router.post("/incidents/{iid}/analyze", status_code=202)
    def analyze(iid: str):
        with factory() as session:
            if not session.get(Incident, iid):
                raise HTTPException(404, "Incident not found")
            paths = [
                Path(row.path)
                for row in session.scalars(
                    select(VideoAsset)
                    .where(VideoAsset.incident_id == iid)
                    .order_by(VideoAsset.created_at, VideoAsset.id)
                )
            ]
        try:
            active_manifest()
        except ModelUnavailable as exc:
            raise HTTPException(503, {"code": "MODEL UNAVAILABLE", "message": str(exc)}) from None
        if not paths:
            raise HTTPException(422, "Upload at least one camera view")

        def operation(progress):
            progress(15)
            result = predict(paths)
            progress(95)
            with factory.begin() as session:
                session.add(
                    Prediction(
                        incident_id=iid, model_version=result["model_version"], result=result
                    )
                )

        try:
            jid = app.state.runner.submit(iid, "inference", operation)
        except QueueFull as exc:
            raise HTTPException(429, str(exc)) from None
        return {"job_id": jid}

    app.include_router(router)
