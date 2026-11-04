import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
)


def metrics(y, probabilities, labels):
    y, probabilities = np.asarray(y), np.asarray(probabilities)
    if probabilities.shape != (len(y), len(labels)) or not np.isfinite(probabilities).all():
        raise ValueError("Invalid probability shape or nonfinite value")
    if not np.allclose(probabilities.sum(axis=1), 1) or (probabilities < 0).any():
        raise ValueError("Probabilities must sum to one")
    prediction = probabilities.argmax(axis=1)
    indices = list(range(len(labels)))
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "report": classification_report(
            y, prediction, labels=indices, target_names=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y, prediction, labels=indices).tolist(),
        "class_distribution": np.bincount(y, minlength=len(labels)).tolist(),
        "error_indices": np.flatnonzero(prediction != y).tolist(),
    }


def calibrate(logits, labels, split):
    if split != "validation":
        raise ValueError("Calibration requires validation data, never test data")
    logits, labels = np.asarray(logits), np.asarray(labels)
    if len(labels) < 2 or not np.isfinite(logits).all():
        raise ValueError("Calibration requires finite validation logits")
    result = minimize_scalar(
        lambda t: log_loss(
            labels, softmax(logits / t, axis=1), labels=list(range(logits.shape[1]))
        ),
        bounds=(0.1, 10),
        method="bounded",
    )
    return float(result.x)


def reliability(y, probabilities, bins=10):
    confidence = probabilities.max(axis=1)
    correct = probabilities.argmax(axis=1) == y
    rows = []
    for i in range(bins):
        selected = (confidence >= i / bins) & (
            (confidence < (i + 1) / bins) if i < bins - 1 else (confidence <= 1)
        )
        if selected.any():
            rows.append(
                {
                    "count": int(selected.sum()),
                    "confidence": float(confidence[selected].mean()),
                    "accuracy": float(correct[selected].mean()),
                }
            )
    return {
        "bins": rows,
        "ece": sum(r["count"] * abs(r["confidence"] - r["accuracy"]) for r in rows) / len(y),
    }


def decision(probabilities, classes, threshold=0.65, calibrated=False):
    index = int(np.argmax(probabilities))
    confidence = float(probabilities[index])
    return {
        "status": "INCONCLUSIVE" if confidence < threshold else "PREDICTED",
        "label": None if confidence < threshold else classes[index],
        "confidence": confidence,
        "confidence_kind": "validation-calibrated probability"
        if calibrated
        else "uncalibrated model score",
        "probabilities": {
            name: float(value) for name, value in zip(classes, probabilities, strict=True)
        },
    }


def plot_reliability(result, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.plot(
        [r["confidence"] for r in result["bins"]], [r["accuracy"] for r in result["bins"]], "o-"
    )
    ax.set(
        xlabel="Mean confidence",
        ylabel="Observed accuracy",
        xlim=(0, 1),
        ylim=(0, 1),
        title="Validation reliability (research only)",
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
