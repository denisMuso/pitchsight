from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.db import Match
from backend.main import create_app
from pitchsight.data.sync import seed_demo


def test_demo_idempotent_and_api(tmp_path):
    app = create_app(tmp_path / "test.sqlite", "demo")
    with TestClient(app) as client:
        seed_demo(app.state.factory)
        with app.state.factory() as session:
            assert session.scalar(select(func.count()).select_from(Match)) == 8
        assert client.get("/ready").status_code == 200
        assert len(client.get("/api/competitions").json()) == 2
        page = client.get("/api/matches?competition=demo-PL&limit=2").json()
        assert page["total"] == 4
        assert len(page["items"]) == 2
        assert page["items"][0]["provenance"] == "DEMO DATA"
        assert client.get("/api/matches/demo-0").status_code == 200
        assert client.get("/api/matches/missing").status_code == 404
        assert client.get("/api/matches?limit=0").status_code == 422
        assert client.get("/api/standings").json()["items"] == []


def test_live_does_not_seed(tmp_path):
    app = create_app(tmp_path / "live.sqlite", "live")
    with TestClient(app) as client:
        assert client.get("/api/matches").json()["total"] == 0


def test_refresh_is_rate_limited_and_demo_rejected(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("backend.main.sync_matches", lambda factory: calls.append(factory))
    with TestClient(create_app(tmp_path / "live.sqlite", "live")) as client:
        assert client.post("/api/sync").status_code == 200
        assert client.post("/api/sync").status_code == 429
        assert len(calls) == 1
    with TestClient(create_app(tmp_path / "demo.sqlite", "demo")) as client:
        assert client.post("/api/sync").status_code == 409
