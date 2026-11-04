from fastapi.testclient import TestClient

from backend.main import create_app


def test_browser_origin_and_request_size(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite", "demo")) as client:
        assert (
            client.post(
                "/api/incidents", json={"title": "x"}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/incidents", json={"title": "x"}, headers={"Origin": "http://127.0.0.1:5173"}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/incidents", content=b"x", headers={"Content-Length": str(200 * 1024 * 1024)}
            ).status_code
            == 413
        )
