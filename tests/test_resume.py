import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")


def test_training_resume_checks_and_equivalence(tmp_path, monkeypatch):
    from pitchsight.training.run import synthetic, train_temporal

    monkeypatch.setattr("pitchsight.training.run.mlflow.log_metrics", lambda *a, **k: None)
    config = json.loads(Path("configs/smoke.json").read_text()) | {"epochs": 1}
    splits, fingerprint, classes = synthetic(config)
    first, _, result = train_temporal(splits, config, tmp_path, classes, fingerprint)
    resumed, _, resumed_result = train_temporal(
        splits, config, tmp_path, classes, fingerprint, tmp_path / "resume.pt"
    )
    for key, value in first.state_dict().items():
        assert torch.equal(value, resumed.state_dict()[key])
    assert resumed_result["history"] == result["history"]
    with pytest.raises(ValueError, match="mismatch"):
        train_temporal(splits, config, tmp_path, classes, "wrong", tmp_path / "resume.pt")
