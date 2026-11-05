import json
from pathlib import Path

import pytest

from pitchsight.ml.dataset import ACTION_CLASSES
from pitchsight.training.preflight import dataset_summary, preflight, validate_config


def config():
    return json.loads(Path("configs/rtx3060.json").read_text())


@pytest.mark.parametrize(
    "key,value",
    [
        ("batch_size", True),
        ("threshold", 2),
        ("learning_rate", float("nan")),
        ("fusion", "invalid"),
    ],
)
def test_invalid_configuration(key, value):
    settings = config()
    settings[key] = value
    with pytest.raises(ValueError):
        validate_config(settings)


def test_missing_dataset_blocks_readiness(tmp_path):
    result = preflight(config(), tmp_path, tmp_path)
    assert result["status"] == "blocked"
    assert any(
        c["name"] == "Authorized dataset" and c["status"] == "blocked" for c in result["checks"]
    )


def test_dataset_audit_reports_counts_and_leakage(tmp_path):
    for split in ("Train", "Valid", "Test"):
        actions = {}
        for i, label in enumerate(ACTION_CLASSES):
            folder = tmp_path / split / f"action_{i}"
            folder.mkdir(parents=True)
            (folder / "clip_0.mp4").write_bytes(f"{split}-{i}".encode())
            actions[str(i)] = {"Action class": label, "Clips": [{}]}
        (tmp_path / split / "annotations.json").write_text(json.dumps({"Actions": actions}))
    result = dataset_summary(tmp_path, config())
    assert result["splits"]["train"]["incidents"] == 8
    assert result["decode_checked"] is False
    assert result["feature_array_bytes"] == 24 * 2 * 8 * 576 * 4
    (tmp_path / "Test/action_0/clip_0.mp4").write_bytes(b"Train-0")
    with pytest.raises(ValueError, match="leakage"):
        dataset_summary(tmp_path, config())
