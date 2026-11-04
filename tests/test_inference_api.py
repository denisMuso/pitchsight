from fastapi.testclient import TestClient

from backend.main import create_app


def test_no_fake_inference(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app(tmp_path / "test.sqlite", "demo")) as client:
        assert client.get("/api/models").json()["status"] == "MODEL UNAVAILABLE"
        iid = client.post("/api/incidents", json={"title": "test"}).json()["id"]
        response = client.post(f"/api/incidents/{iid}/analyze")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "MODEL UNAVAILABLE"
        assert client.get(f"/api/incidents/{iid}").json()["predictions"] == []
