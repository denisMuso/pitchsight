# ruff: noqa: E402
import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from pitchsight.evaluation.metrics import calibrate, decision, metrics, reliability
from pitchsight.ml.dataset import Record, validate_splits
from pitchsight.ml.models import TemporalFusion


@pytest.mark.parametrize("fusion", ["mean", "attention"])
def test_multiview_gradient_mask_and_checkpoint(tmp_path, fusion):
    torch.manual_seed(2)
    model = TemporalFusion(16, 3, 8, fusion)
    x = torch.randn(3, 2, 8, 16, requires_grad=True)
    mask = torch.tensor([[True, False], [True, True], [False, True]])
    logits = model(x, mask)
    assert logits.shape == (3, 3)
    logits.sum().backward()
    assert torch.isfinite(x.grad).all()
    assert x.grad[0, 1].abs().sum() == 0
    altered = x.detach().clone()
    altered[0, 1] = float("nan")
    assert torch.allclose(model(x, mask)[0], model(altered, mask)[0])
    path = tmp_path / "model.pt"
    torch.save(model.state_dict(), path)
    reloaded = TemporalFusion(16, 3, 8, fusion)
    reloaded.load_state_dict(torch.load(path, weights_only=True))
    assert torch.allclose(model(x, mask), reloaded(x, mask))
    with pytest.raises(ValueError):
        model(x, torch.zeros_like(mask))


def test_split_leakage():
    records = [
        Record("a", "train", 0, ["a.mp4"], ["hash"]),
        Record("b", "test", 0, ["b.mp4"], ["hash"]),
    ]
    with pytest.raises(ValueError, match="leakage"):
        validate_splits(records)
    records[1].hashes = ["other"]
    validate_splits(records)
    records[1].incident_id = "a"
    with pytest.raises(ValueError, match="leakage"):
        validate_splits(records)


def test_metrics_calibration_and_abstention():
    y = np.array([0, 1, 1, 0])
    p = np.array([[0.9, 0.1], [0.1, 0.9], [0.4, 0.6], [0.8, 0.2]])
    result = metrics(y, p, ["a", "b"])
    assert result["accuracy"] == 1
    assert result["confusion_matrix"] == [[2, 0], [0, 2]]
    assert result["report"]["macro avg"]["f1-score"] == 1
    assert reliability(y, p)["ece"] == pytest.approx(0.2)
    assert decision([0.51, 0.49], ["a", "b"])["status"] == "INCONCLUSIVE"
    assert decision([0.9, 0.1], ["a", "b"])["label"] == "a"
    with pytest.raises(ValueError, match="validation"):
        calibrate(np.log(p), y, "test")
    assert 0.1 <= calibrate(np.log(p), y, "validation") <= 10


def test_baseline_numeric_export(tmp_path):
    from pitchsight.training.run import baseline, synthetic

    splits, _, classes = synthetic({"seed": 17})
    result = baseline(splits, classes, tmp_path)
    exported = json.loads((tmp_path / "baseline.json").read_text())
    assert len(exported["coef"]) == 3
    assert 0 <= result["accuracy"] <= 1


def test_registry_unavailable(tmp_path):
    from pitchsight.inference.registry import ModelUnavailable, active_manifest, read_manifest

    with pytest.raises(ModelUnavailable, match="no valid"):
        active_manifest(tmp_path)
    (tmp_path / "bad.json").write_text('{"schema_version":99}')
    with pytest.raises(ModelUnavailable):
        read_manifest(tmp_path / "bad.json")
