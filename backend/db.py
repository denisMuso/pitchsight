import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    provenance: Mapped[str]


class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[str] = mapped_column(primary_key=True)
    competition_id: Mapped[str] = mapped_column(ForeignKey("competitions.id"))
    year: Mapped[int]


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    provenance: Mapped[str]


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[str] = mapped_column(primary_key=True)
    competition_id: Mapped[str] = mapped_column(ForeignKey("competitions.id"), index=True)
    season_id: Mapped[str] = mapped_column(ForeignKey("seasons.id"))
    home_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    away_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    kickoff: Mapped[str] = mapped_column(index=True)
    status: Mapped[str]
    home_score: Mapped[int | None]
    away_score: Mapped[int | None]
    provenance: Mapped[str]
    updated_at: Mapped[str] = mapped_column(default=now)


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (UniqueConstraint("season_id", "team_id", "group_name", "stage"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey("seasons.id"))
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    group_name: Mapped[str] = mapped_column(default="")
    stage: Mapped[str] = mapped_column(default="REGULAR_SEASON")
    position: Mapped[int]
    points: Mapped[int]
    played: Mapped[int]
    provenance: Mapped[str]


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[str] = mapped_column(default=now)
    mode: Mapped[str]
    status: Mapped[str]
    detail: Mapped[str]


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    match_id: Mapped[str | None] = mapped_column(ForeignKey("matches.id"))
    created_at: Mapped[str] = mapped_column(default=now)


class VideoAsset(Base):
    __tablename__ = "video_assets"
    __table_args__ = (UniqueConstraint("incident_id", "view_name"),)
    id: Mapped[str] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    view_name: Mapped[str]
    path: Mapped[str]
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    kind: Mapped[str]
    state: Mapped[str] = mapped_column(index=True)
    progress: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    model_version: Mapped[str]
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    decision: Mapped[str]
    comments: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[str] = mapped_column(default=now)


def database(path: Path | None = None):
    path = path or Path(os.getenv("PITCHSIGHT_DATA_DIR", "data")) / "pitchsight.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False, "timeout": 30}
    )

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
