"""Render recorded test metrics without rerunning or selecting experiments."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--note", default="Research metrics; not an officiating verdict")
    args = parser.parse_args()
    report = json.loads((args.run / "metrics.json").read_text())
    manifest = json.loads((args.run / "manifest.json").read_text())
    if report["temporal"]["split"] != "test":
        raise ValueError("This figure is for a held-out test report only")
    labels = manifest["classes"]
    matrix = np.asarray(report["temporal"]["confusion_matrix"])
    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 7), layout="constrained")
    heat = left.imshow(matrix, cmap="Blues")
    left.set_xticks(range(len(labels)), labels, rotation=40, ha="right")
    left.set_yticks(range(len(labels)), labels)
    left.set(
        xlabel="Predicted class",
        ylabel="Actual class",
        title="Temporal model: test confusion counts",
    )
    for i in range(len(labels)):
        for j in range(len(labels)):
            left.text(
                j,
                i,
                str(matrix[i, j]),
                ha="center",
                va="center",
                color="white" if matrix[i, j] > matrix.max() / 2 else "black",
            )
    fig.colorbar(heat, ax=left, shrink=0.7)
    y = np.arange(len(labels))
    for offset, key, color in ((-0.18, "temporal", "#287d8e"), (0.18, "baseline", "#d58b30")):
        right.barh(
            y + offset,
            [report[key]["report"][label]["f1-score"] for label in labels],
            height=0.34,
            label=key.title(),
            color=color,
        )
    right.set_yticks(y, labels)
    right.invert_yaxis()
    right.set(
        xlim=(0, 1), xlabel="F1 score", title=f"Per-class test F1 ({int(matrix.sum())} incidents)"
    )
    right.legend(loc="lower right")
    fig.suptitle(
        f"PitchSight | {manifest['version']}\n{args.note}",
        fontsize=14,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
