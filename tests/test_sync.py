import httpx
import pytest
from sqlalchemy import func, select

from backend.db import Match, SyncLog, database
from pitchsight.data.provider import FootballData, ProviderError
from pitchsight.data.sync import sync_matches


def test_live_upsert_partial_standings_and_missing_token(tmp_path, monkeypatch):
    engine, factory = database(tmp_path / "sync.sqlite")
    payload = {
        "competition": {"name": "Premier League"},
        "matches": [
            {
                "id": 1,
                "season": {"id": 9, "startDate": "2025-08-01"},
                "homeTeam": {"id": 10, "name": "Fixture Home"},
                "awayTeam": {"id": 20, "name": "Fixture Away"},
                "score": {"fullTime": {"home": 1, "away": 0}},
                "utcDate": "2025-09-01T12:00:00Z",
                "status": "FINISHED",
            }
        ],
    }
    transport = httpx.MockTransport(
        lambda request: (
            httpx.Response(403)
            if request.url.path.endswith("standings")
            else httpx.Response(200, json=payload)
        )
    )
    client = FootballData("fixture-token", transport, interval=0)
    for _ in range(2):
        sync_matches(factory, ["PL"], client)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Match)) == 1
        assert session.get(Match, "1").provenance == "LIVE API"
        assert session.scalar(select(SyncLog).order_by(SyncLog.id.desc())).status == "partial"
    client.close()
    monkeypatch.delenv("FOOTBALL_DATA_TOKEN", raising=False)
    with pytest.raises(ProviderError, match="required"):
        sync_matches(factory)
    with factory() as session:
        assert session.scalar(select(SyncLog).order_by(SyncLog.id.desc())).status == "failed"
    engine.dispose()
