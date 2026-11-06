"""Post-training audit of a fixed checkpoint; never selects models or thresholds."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import softmax

from pitchsight.evaluation.metrics import metrics, reliability


def selective_metrics(y, probabilities, threshold):
    y, probabilities = np.asarray(y), np.asarray(probabilities)
    accepted = probabilities.max(axis=1) >= threshold
    correct = probabilities.argmax(axis=1) == y
    return {
        "threshold": threshold,
        "accepted": int(accepted.sum()),
        "abstained": int((~accepted).sum()),
        "coverage": float(accepted.mean()),
        "accepted_accuracy": float(correct[accepted].mean()) if accepted.any() else None,
    }


def paired_bootstrap(y, model, baseline, draws=2000, seed=17):
    """Paired incident bootstrap, not a guarantee or a game-clustered interval."""
    y = np.asarray(y)
    delta = (np.asarray(model).argmax(axis=1) == y).astype(float)
    delta -= np.asarray(baseline).argmax(axis=1) == y
    rng = np.random.default_rng(seed)
    estimates = np.array(
        [rng.choice(delta, size=len(delta), replace=True).mean() for _ in range(draws)]
    )
    return {
        "accuracy_delta": float(delta.mean()),
        "percentile_95_interval": np.quantile(estimates, [0.025, 0.975]).tolist(),
        "bootstrap_draws": draws,
        "seed": seed,
        "unit": "incident",
        "limitation": "Assumes independent incidents; shared-game correlations are not modeled",
    }


def audit(run, dataset):
    import torch

    from pitchsight.inference.registry import read_manifest
    from pitchsight.ml.dataset import ACTION_CLASSES, load_soccernet
    from pitchsight.ml.features import Encoder, cached_features
    from pitchsight.ml.models import TemporalFusion, device

    manifest, checkpoint = read_manifest(run / "manifest.json")
    records, fingerprint, _ = load_soccernet(dataset)
    if fingerprint != manifest.dataset_fingerprint or manifest.classes != ACTION_CLASSES:
        raise ValueError("Dataset fingerprint or class order changed since training")
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if saved["metadata"]["fingerprint"] != fingerprint:
        raise ValueError("Checkpoint metadata fingerprint mismatch")
    model = TemporalFusion(**manifest.architecture).to(device()).eval()
    model.load_state_dict(saved["state_dict"], strict=True)
    exported = json.loads((run / "baseline.json").read_text())
    if exported["classes"] != manifest.classes:
        raise ValueError("Baseline class order mismatch")
    encoder = Encoder()
    output = {
        "model_version": manifest.version,
        "checkpoint_sha256": manifest.sha256,
        "dataset_fingerprint": fingerprint,
        "provenance": manifest.provenance,
        "policy": "Fixed checkpoint, temperature and threshold; no selection on test",
        "splits": {},
    }
    for split in ("validation", "test"):
        chosen = [r for r in records if r.split == split]
        probabilities, baseline_probabilities, first_view, labels, rows = [], [], [], [], []
        for record in chosen:
            x = np.zeros((1, manifest.views, manifest.frames, 576), dtype=np.float32)
            mask = np.zeros((1, manifest.views), dtype=bool)
            for view, path in enumerate(record.views[: manifest.views]):
                x[0, view] = cached_features(
                    path,
                    Path("artifacts/features"),
                    encoder,
                    fingerprint,
                    record.incident_id,
                    view,
                    manifest.frames,
                    manifest.size,
                )
                mask[0, view] = True
            with torch.inference_mode():
                tensor = torch.tensor(x, device=device())
                logits = model(tensor, torch.tensor(mask, device=device())).cpu().numpy()[0]
                if split == "validation":
                    one = mask.copy()
                    one[:, 1:] = False
                    first_view.append(
                        softmax(model(tensor, torch.tensor(one, device=device())).cpu().numpy()[0])
                    )
            p = softmax(logits / manifest.temperature)
            pooled = (x.mean(axis=2) * mask[..., None]).sum(axis=1) / mask.sum(axis=1)[:, None]
            b = softmax(pooled @ np.asarray(exported["coef"]).T + exported["intercept"], axis=1)[0]
            probabilities.append(p)
            baseline_probabilities.append(b)
            labels.append(record.label)
            predicted = int(p.argmax())
            rows.append(
                {
                    "incident_id": record.incident_id,
                    "actual": manifest.classes[record.label],
                    "predicted": manifest.classes[predicted],
                    "correct": predicted == record.label,
                    "confidence": float(p.max()),
                    "abstained": bool(p.max() < manifest.threshold),
                    "probabilities": p.tolist(),
                    "baseline_probabilities": b.tolist(),
                }
            )
        p, b, y = np.asarray(probabilities), np.asarray(baseline_probabilities), np.asarray(labels)
        report = {
            "temporal": metrics(y, p, manifest.classes),
            "baseline": metrics(y, b, manifest.classes),
            "selective": selective_metrics(y, p, manifest.threshold),
            "reliability": reliability(y, p),
            "paired_comparison": paired_bootstrap(y, p, b),
            "incidents": rows,
        }
        if split == "validation":
            report["first_view_only_ablation"] = metrics(
                y, np.asarray(first_view), manifest.classes
            )
            report["ablation_note"] = (
                "Same multi-view-trained checkpoint with other views masked; not a separately trained single-view baseline"
            )
        output["splits"][split] = report
        print(f"Audited {split}: {len(chosen)} incidents", flush=True)
    (run / "evaluation-audit.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    args = parser.parse_args()
    audit(args.run, args.dataset)


if __name__ == "__main__":
    main()
