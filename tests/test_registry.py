import json

import pytest

torch = pytest.importorskip("torch")


def manifest_fixture(tmp_path):
    from pitchsight.ml.dataset import digest_file
    from pitchsight.ml.models import TemporalFusion

    root = tmp_path / "artifacts"
    run = root / "runs/fixture"
    run.mkdir(parents=True)
    model = TemporalFusion(576, 2, 4, "mean")
    torch.save(
        {
            "state_dict": model.state_dict(),
            "metadata": {"classes": ["a", "b"], "fingerprint": "unit-test-only"},
        },
        run / "model.pt",
    )
    manifest = {
        "schema_version": 1,
        "version": "unit-test-only",
        "model_type": "temporal-fusion",
        "checkpoint": "model.pt",
        "sha256": digest_file(run / "model.pt"),
        "architecture": {"features": 576, "classes": 2, "hidden": 4, "fusion": "mean"},
        "classes": ["a", "b"],
        "dataset_fingerprint": "unit-test-only",
        "provenance": "AUTHORIZED LABELED DATA",
        "encoder": "mobilenet_v3_small-IMAGENET1K_V1",
        "preprocessing": "rgb-square-imagenet-normalization-v1",
        "frames": 8,
        "size": 160,
        "views": 2,
        "temperature": 1.0,
        "calibration_split": "validation",
        "threshold": 0.65,
        "hardware": {},
        "metrics_provenance": "unit test, not a real model",
        "run_id": "unit-test",
    }
    path = run / "manifest.json"
    path.write_text(json.dumps(manifest))
    return root, path, manifest


def test_manifest_gates_and_hash(tmp_path):
    from pitchsight.inference.registry import (
        ModelUnavailable,
        active_manifest,
        read_manifest,
        register,
    )

    root, path, manifest = manifest_fixture(tmp_path)
    register(path, root)
    assert active_manifest(root)[0].version == "unit-test-only"
    for field, invalid in [
        ("provenance", "SYNTHETIC SMOKE TEST"),
        ("preprocessing", "unknown"),
        ("checkpoint", "../../../outside.pt"),
        ("calibration_split", "test"),
        ("metrics_provenance", "validation-only development; no held-out test evaluation"),
    ]:
        path.write_text(json.dumps(manifest | {field: invalid}))
        with pytest.raises(ModelUnavailable):
            read_manifest(path)
    path.write_text(json.dumps(manifest))
    (path.parent / "model.pt").write_bytes(b"changed")
    with pytest.raises(ModelUnavailable, match="changed"):
        active_manifest(root)


def test_real_checkpoint_inference_path(tmp_path, monkeypatch):
    import numpy as np

    from pitchsight.inference.registry import predict, register

    root, path, manifest = manifest_fixture(tmp_path)
    register(path, root)
    monkeypatch.setattr("pitchsight.ml.features.Encoder", lambda _: None)
    monkeypatch.setattr(
        "pitchsight.ml.features.cached_features", lambda *args: np.zeros((8, 576), dtype=np.float32)
    )
    result = predict([tmp_path / "fixture.mp4"], root)
    assert result["status"] in ("PREDICTED", "INCONCLUSIVE")
    assert result["views_used"] == 1
    assert sum(result["probabilities"].values()) == pytest.approx(1)
    assert result["confidence_kind"] == "validation-calibrated probability"
