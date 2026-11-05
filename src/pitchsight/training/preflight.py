"""Read-only training checks. No downloads, feature extraction or training."""

import argparse
import json
import math
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pitchsight.ml.dataset import ACTION_CLASSES, load_soccernet


def validate_config(config):
    for key in (
        "epochs",
        "batch_size",
        "accumulation",
        "frames",
        "views",
        "patience",
        "hidden",
        "size",
    ):
        value = config.get(key)
        if type(value) is not int or value < 1:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("seed", "num_workers"):
        if type(config.get(key)) is not int or config[key] < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
    for key in ("learning_rate", "weight_decay", "threshold"):
        value = config.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{key} must be finite")
    if config["learning_rate"] <= 0 or config["weight_decay"] < 0:
        raise ValueError("Invalid optimizer parameters")
    if not 0 <= config["threshold"] <= 1:
        raise ValueError("threshold must be between zero and one")
    if config.get("fusion") not in ("mean", "attention"):
        raise ValueError("fusion must be mean or attention")
    if config["frames"] > 64 or not 32 <= config["size"] <= 512:
        raise ValueError("Decoder requires frames <= 64 and size between 32 and 512")


def dataset_summary(root, config):
    records, fingerprint, excluded = load_soccernet(root)
    splits = {}
    for split in ("train", "validation", "test"):
        selected = [r for r in records if r.split == split]
        if not selected:
            raise ValueError(f"Empty {split} split")
        counts = Counter(r.label for r in selected)
        missing = [name for i, name in enumerate(ACTION_CLASSES) if not counts[i]]
        if split == "train" and missing:
            raise ValueError(f"Training split missing classes: {', '.join(missing)}")
        splits[split] = {
            "incidents": len(selected),
            "class_counts": {name: counts[i] for i, name in enumerate(ACTION_CLASSES)},
            "missing_classes": missing,
            "view_counts": dict(Counter(len(r.views) for r in selected)),
            "truncated_incidents": sum(len(r.views) > config["views"] for r in selected),
        }
    feature_bytes = len(records) * config["views"] * config["frames"] * 576 * 4
    return {
        "fingerprint": fingerprint,
        "splits": splits,
        "excluded_incidents": len(excluded),
        "feature_array_bytes": feature_bytes,
        "approx_host_feature_bytes": feature_bytes * 2,
        "decode_checked": False,
    }


def preflight(config, dataset=None, output=Path("artifacts")):
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    try:
        validate_config(config)
    except ValueError as exc:
        add("Configuration", "blocked", str(exc))
        return {"status": "blocked", "checks": checks, "dataset": None}
    add("Configuration", "passed", "Validated training dimensions, optimizer and threshold")
    try:
        import torch

        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            add(
                "Compute",
                "passed",
                f"{torch.cuda.get_device_name(0)}; {free / 2**30:.1f} GiB free / {total / 2**30:.1f} GiB total VRAM",
            )
        else:
            add(
                "Compute",
                "warning",
                "CUDA unavailable; training will use CPU (or MPS on supported Macs)",
            )
    except (ImportError, RuntimeError, OSError) as exc:
        add("Compute", "blocked", f"PyTorch unavailable: {type(exc).__name__}")
    summary = None
    if dataset is None:
        add(
            "Authorized dataset",
            "blocked",
            "SoccerNet access pending; pass --dataset after extracting Train/Valid/Test",
        )
    else:
        try:
            summary = dataset_summary(Path(dataset), config)
            add(
                "Authorized dataset",
                "passed",
                "Schema, files, content hashes, split separation and training labels checked",
            )
            add(
                "Video decoding",
                "warning",
                "Not decoded by preflight; feature extraction validates selected clips",
            )
        except (ValueError, OSError, TypeError, KeyError) as exc:
            add("Authorized dataset", "blocked", str(exc))
    existing = Path(output).resolve()
    while not existing.exists():
        existing = existing.parent
    free_disk = shutil.disk_usage(existing).free
    required = (summary["feature_array_bytes"] * 2 if summary else 0) + 2**30
    add(
        "Disk space",
        "passed" if free_disk >= required else "blocked",
        f"{free_disk / 2**30:.1f} GiB free; estimated cache/checkpoint allowance {required / 2**30:.1f} GiB (excludes dataset downloads)",
    )
    add(
        "Memory estimate",
        "warning",
        "Feature estimates exclude decoder, encoder, optimizer and OS memory; available VRAM is not an OOM guarantee",
    )
    return {
        "status": "blocked" if any(c["status"] == "blocked" for c in checks) else "ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "dataset": summary,
        "effective_batch_size": config["batch_size"] * config["accumulation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/rtx3060.json"))
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/preflight.json"))
    args = parser.parse_args()
    result = preflight(json.loads(args.config.read_text()), args.dataset, args.output.parent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "ready" else 2)


if __name__ == "__main__":
    main()
