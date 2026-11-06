import numpy as np
import pytest

from pitchsight.evaluation.audit import paired_bootstrap, selective_metrics


def test_abstention_no_acceptance_is_not_zero_accuracy():
    p = np.array([[0.55, 0.45], [0.4, 0.6]])
    report = selective_metrics([0, 1], p, 0.65)
    assert report["accepted"] == 0
    assert report["coverage"] == 0
    assert report["accepted_accuracy"] is None
    report = selective_metrics([0, 0], p, 0.6)
    assert report["coverage"] == 0.5
    assert report["accepted_accuracy"] == 0


def test_paired_comparison_keeps_incident_pairing():
    p = np.array([[0.9, 0.1], [0.2, 0.8]])
    same = paired_bootstrap([0, 1], p, p)
    assert same["percentile_95_interval"] == [0, 0]
    opposite = paired_bootstrap([0, 1], p, p[:, ::-1])
    assert opposite["accuracy_delta"] == pytest.approx(1)
    assert opposite["percentile_95_interval"] == [1, 1]
