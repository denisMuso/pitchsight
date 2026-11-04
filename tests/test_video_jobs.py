from threading import Event

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.db import Incident, Job, database
from backend.main import create_app
from pitchsight.jobs.runner import LocalRunner, QueueFull
from pitchsight.video.processing import browser_copy, executable, process_video


def make_video(path):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened()
    for i in range(20):
        writer.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
    writer.release()


def test_generated_video(tmp_path):
    source = tmp_path / "fixture.avi"
    make_video(source)
    metadata = process_video(source, tmp_path / "out", count=4, size=64)
    assert metadata["duration"] == 2
    assert metadata["sample_indices"] == [0, 6, 12, 19]
    frames = np.load(tmp_path / "out/frames.npy")
    assert frames.shape == (4, 64, 64, 3)
    assert frames[0].mean() < frames[-1].mean()
    corrupt = tmp_path / "bad.mp4"
    corrupt.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="signature"):
        process_video(corrupt, tmp_path / "bad")


@pytest.mark.skipif(not executable("ffmpeg"), reason="FFmpeg not installed")
def test_real_ffmpeg_playback(tmp_path):
    source = tmp_path / "fixture.avi"
    make_video(source)
    playback = tmp_path / "playback.mp4"
    browser_copy(source, playback)
    metadata = process_video(playback, tmp_path / "decoded")
    assert metadata["duration"] == pytest.approx(2, abs=0.1)


def test_upload_review_multiview(tmp_path, monkeypatch):
    # Conversion mocked here; decoding is real. FFmpeg integration is tested separately.
    monkeypatch.setattr(
        "backend.incidents.browser_copy", lambda src, target: target.write_bytes(b"test")
    )
    app = create_app(tmp_path / "test.sqlite", "demo")
    source = tmp_path / "fixture.avi"
    make_video(source)
    with TestClient(app) as client:
        iid = client.post("/api/incidents", json={"title": "Synthetic engineering fixture"}).json()[
            "id"
        ]
        for view in ("main", "replay"):
            response = client.post(
                f"/api/incidents/{iid}/videos",
                data={"authorized": "true", "view_name": view},
                files={"file": ("../../fixture.avi", source.read_bytes(), "video/avi")},
            )
            assert response.status_code == 202, response.text
        detail = client.get(f"/api/incidents/{iid}").json()
        assert len(detail["views"]) == 2
        assert not (tmp_path / "fixture.mp4").exists()
        bad = client.post(
            f"/api/incidents/{iid}/videos",
            data={"authorized": "true", "view_name": "bad"},
            files={"file": ("bad.mp4", b"bad", "video/mp4")},
        )
        assert bad.status_code == 422
        monkeypatch.setattr("backend.incidents.MAX_BYTES", 2)
        large = client.post(
            f"/api/incidents/{iid}/videos",
            data={"authorized": "true", "view_name": "large"},
            files={"file": ("file.avi", b"123", "video/avi")},
        )
        assert large.status_code == 413
        assert (
            client.post(
                f"/api/incidents/{iid}/reviews",
                json={"decision": "INCONCLUSIVE", "comments": "Engineering test only"},
            ).status_code
            == 201
        )
        assert len(client.get(f"/api/incidents/{iid}").json()["reviews"]) == 1


def test_jobs_bounded_and_recovered(tmp_path):
    engine, factory = database(tmp_path / "jobs.sqlite")
    with factory.begin() as session:
        session.add(Incident(id="i", title="test"))
        session.flush()
        session.add(Job(id="old", incident_id="i", kind="test", state="running"))
    runner = LocalRunner(factory, capacity=1)
    gate = Event()
    jid = runner.submit("i", "test", lambda progress: gate.wait(5))
    try:
        with pytest.raises(QueueFull):
            runner.submit("i", "test", lambda _: None)
    finally:
        gate.set()
        runner.close()
    with factory() as session:
        assert session.get(Job, "old").state == "failed"
        assert session.get(Job, jid).state == "completed"
    engine.dispose()
