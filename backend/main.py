import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, text

from backend.db import Competition, Match, Standing, SyncLog, Team, database
from pitchsight.data.sync import seed_demo

load_dotenv()


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    provenance: str


class MatchOut(BaseModel):
    id: str
    competition_id: str
    kickoff: str
    status: str
    home: str
    away: str
    home_score: int | None
    away_score: int | None
    provenance: str


class MatchPage(BaseModel):
    items: list[MatchOut]
    total: int
    offset: int
    limit: int


def create_app(db_path: Path | None = None, mode: str | None = None):
    mode = mode or os.getenv("PITCHSIGHT_MODE", "demo")
    if mode not in ("demo", "live"):
        raise ValueError("PITCHSIGHT_MODE must be demo or live")
    engine, factory = database(db_path)

    @asynccontextmanager
    async def lifespan(app):
        if mode == "demo":
            seed_demo(factory)
        yield
        engine.dispose()

    app = FastAPI(title="PitchSight Research API", lifespan=lifespan)
    app.state.factory = factory
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": mode, "research_only": True}

    @app.get("/ready")
    def ready():
        with factory() as session:
            session.execute(text("SELECT 1"))
        return {"database": "ready", "model": "MODEL UNAVAILABLE"}

    @app.get("/api/competitions", response_model=list[CompetitionOut])
    def competitions():
        with factory() as session:
            return session.scalars(
                select(Competition).where(
                    Competition.provenance == ("DEMO DATA" if mode == "demo" else "LIVE API")
                )
            ).all()

    @app.get("/api/teams", response_model=list[CompetitionOut])
    def teams(limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
        with factory() as session:
            return session.scalars(
                select(Team)
                .where(Team.provenance == ("DEMO DATA" if mode == "demo" else "LIVE API"))
                .offset(offset)
                .limit(limit)
            ).all()

    def serialize(row, session):
        return MatchOut(
            id=row.id,
            competition_id=row.competition_id,
            kickoff=row.kickoff,
            status=row.status,
            home=session.get(Team, row.home_id).name,
            away=session.get(Team, row.away_id).name,
            home_score=row.home_score,
            away_score=row.away_score,
            provenance=row.provenance,
        )

    @app.get("/api/matches", response_model=MatchPage)
    def matches(
        competition: str | None = None,
        status: str | None = None,
        limit: int = Query(25, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        query = select(Match).where(
            Match.provenance == ("DEMO DATA" if mode == "demo" else "LIVE API")
        )
        if competition:
            query = query.where(Match.competition_id == competition)
        if status:
            query = query.where(Match.status == status)
        with factory() as session:
            total = session.scalar(select(func.count()).select_from(query.subquery()))
            rows = session.scalars(
                query.order_by(Match.kickoff, Match.id).offset(offset).limit(limit)
            ).all()
            return MatchPage(
                items=[serialize(row, session) for row in rows],
                total=total,
                offset=offset,
                limit=limit,
            )

    @app.get("/api/matches/{match_id}", response_model=MatchOut)
    def match(match_id: str):
        with factory() as session:
            row = session.get(Match, match_id)
            if not row or row.provenance != ("DEMO DATA" if mode == "demo" else "LIVE API"):
                raise HTTPException(404, "Match not found")
            return serialize(row, session)

    @app.get("/api/standings")
    def standings(season: str | None = None):
        with factory() as session:
            query = select(Standing).where(
                Standing.provenance == ("DEMO DATA" if mode == "demo" else "LIVE API")
            )
            if season:
                query = query.where(Standing.season_id == season)
            rows = session.scalars(query.order_by(Standing.position).limit(100)).all()
            return {
                "items": rows,
                "availability": "AVAILABLE" if rows else "UNAVAILABLE — no standings ingested",
            }

    @app.get("/api/sync/status")
    def sync_status():
        with factory() as session:
            return {
                "items": session.scalars(
                    select(SyncLog).order_by(SyncLog.id.desc()).limit(20)
                ).all()
            }

    return app


app = create_app()
