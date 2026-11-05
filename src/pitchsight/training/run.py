"""Native, spawn-safe training. Synthetic smoke runs cannot be registered for inference."""

import argparse
import json
import random
import time
from dataclasses import asdict
from pathlib import Path

import mlflow
import numpy as np
import torch
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from pitchsight.evaluation.metrics import calibrate, metrics, plot_reliability, reliability
from pitchsight.ml.dataset import ACTION_CLASSES, digest_file, load_soccernet
from pitchsight.ml.features import ENCODER, PREPROCESSING, Encoder, cached_features
from pitchsight.ml.models import TemporalFusion, device
from pitchsight.training.preflight import validate_config

RUN_OUTPUT = None


def progress(output, stage, **details):
    payload = {
        "model_version": output.name,
        "stage": stage,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **details,
    }
    temporary = output / "progress.tmp"
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(output / "progress.json")


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def checkpoint(path, model, metadata):
    temporary = path.with_suffix(".tmp")
    torch.save(
        {
            "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
            "metadata": metadata,
        },
        temporary,
    )
    temporary.replace(path)


def train_temporal(splits, config, output, classes, fingerprint, resume=None):
    target = device()
    features = splits["train"][0].shape[-1]
    model = TemporalFusion(features, len(classes), config["hidden"], config["fusion"]).to(target)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"]
    )
    start, best, stale = 0, float("inf"), 0
    history = []
    amp = target.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    resume_path = output / "resume.pt"
    if resume:
        saved = torch.load(resume, map_location="cpu", weights_only=True)
        if (
            saved["fingerprint"] != fingerprint
            or saved["config"] != config
            or saved["classes"] != classes
        ):
            raise ValueError("Resume dataset, labels or config mismatch")
        model.load_state_dict(saved["state_dict"])
        optimizer.load_state_dict(saved["optimizer"])
        scaler.load_state_dict(saved["scaler"])
        start, best, stale = saved["epoch"] + 1, saved["best"], saved["stale"]
        history = saved.get("history", [])
        torch.set_rng_state(saved["rng"])
        if amp and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state_all(saved["cuda_rng"])
        if not (output / "model.pt").exists():
            raise ValueError("Resume requires the original output directory and best model.pt")
    datasets = {
        split: TensorDataset(
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(mask, dtype=torch.bool),
            torch.tensor(y, dtype=torch.long),
        )
        for split, (x, mask, y) in splits.items()
    }
    counts = np.bincount(splits["train"][2], minlength=len(classes))
    if (counts == 0).any():
        raise ValueError("Training split must represent every configured label")
    weights = torch.tensor(
        counts.sum() / (len(classes) * counts), dtype=torch.float32, device=target
    )
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    metadata = {
        "architecture": {
            "features": features,
            "classes": len(classes),
            "hidden": config["hidden"],
            "fusion": config["fusion"],
        },
        "classes": classes,
        "fingerprint": fingerprint,
    }
    if amp:
        torch.cuda.reset_peak_memory_stats()
    for epoch in range(start, config["epochs"]):
        generator = torch.Generator().manual_seed(config["seed"] + epoch)
        loader = DataLoader(
            datasets["train"],
            batch_size=config["batch_size"],
            shuffle=True,
            generator=generator,
            num_workers=config["num_workers"],
        )
        model.train()
        optimizer.zero_grad(set_to_none=True)
        total = 0.0
        for step, (x, mask, y) in enumerate(loader):
            x, mask, y = x.to(target), mask.to(target), y.to(target)
            # Final accumulation group can contain fewer minibatches.
            group_start = (step // config["accumulation"]) * config["accumulation"]
            group_size = min(config["accumulation"], len(loader) - group_start)
            with torch.autocast(device_type=target.type, enabled=amp):
                loss = loss_fn(model(x, mask), y)
            scaler.scale(loss / group_size).backward()
            total += loss.item() * len(y)
            if (step + 1) % config["accumulation"] == 0 or step + 1 == len(loader):
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), 1)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
        logits = predict_logits(model, datasets["validation"], target, config["batch_size"])
        val_loss = nn.functional.cross_entropy(
            torch.tensor(logits), datasets["validation"].tensors[2]
        ).item()
        history.append(
            {
                "epoch": epoch,
                "train_loss": total / len(datasets["train"]),
                "validation_loss": val_loss,
            }
        )
        mlflow.log_metrics(history[-1], step=epoch)
        print(json.dumps({"epoch": epoch + 1, "validation_loss": val_loss}), flush=True)
        progress(
            output,
            "training",
            epoch=epoch + 1,
            max_epochs=config["epochs"],
            validation_loss=val_loss,
        )
        if val_loss < best:
            best, stale = val_loss, 0
            checkpoint(output / "model.pt", model, metadata)
        else:
            stale += 1
        temporary = resume_path.with_suffix(".tmp")
        torch.save(
            {
                "state_dict": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scaler": scaler.state_dict(),
                "epoch": epoch,
                "best": best,
                "stale": stale,
                "config": config,
                "classes": classes,
                "fingerprint": fingerprint,
                "rng": torch.get_rng_state(),
                "history": history,
                "cuda_rng": torch.cuda.get_rng_state_all() if amp else None,
            },
            temporary,
        )
        temporary.replace(resume_path)
        if stale >= config["patience"]:
            break
    model.load_state_dict(
        torch.load(output / "model.pt", weights_only=True, map_location=target)["state_dict"]
    )
    logits = predict_logits(model, datasets["validation"], target, config["batch_size"])
    temperature = calibrate(logits, splits["validation"][2], "validation")
    probabilities = softmax(logits / temperature, axis=1)
    calibration = reliability(splits["validation"][2], probabilities)
    plot_reliability(calibration, output / "reliability.png")
    # Test split is touched only after training/early stopping/calibration are fixed.
    begin = time.perf_counter()
    test_logits = predict_logits(model, datasets["test"], target, config["batch_size"])
    latency = (time.perf_counter() - begin) * 1000 / len(datasets["test"])
    result = metrics(splits["test"][2], softmax(test_logits / temperature, axis=1), classes)
    result.update(
        {
            "split": "test",
            "temperature": temperature,
            "calibration_split": "validation",
            "reliability": calibration,
            "history": history,
            "classifier_ms_per_incident": latency,
            "peak_cuda_mib": torch.cuda.max_memory_allocated() / 1024**2 if amp else None,
            "device": str(target),
        }
    )
    return model, metadata, result


@torch.inference_mode()
def predict_logits(model, dataset, target, batch_size):
    model.eval()
    result = []
    for x, mask, _ in DataLoader(dataset, batch_size=batch_size, num_workers=0):
        result.append(model(x.to(target), mask.to(target)).cpu().numpy())
    if not result:
        raise ValueError("Empty evaluation split")
    return np.concatenate(result)


def mean_features(x, mask):
    return (x.mean(axis=2) * mask[..., None]).sum(axis=1) / mask.sum(axis=1, keepdims=True)


def baseline(splits, classes, output):
    x, mask, y = splits["train"]
    classifier = LogisticRegression(class_weight="balanced", max_iter=500, random_state=17)
    classifier.fit(mean_features(x, mask), y)
    if list(classifier.classes_) != list(range(len(classes))):
        raise ValueError("Baseline training classes mismatch")
    # Export numeric coefficients as JSON, never an executable pickle.
    (output / "baseline.json").write_text(
        json.dumps(
            {
                "classes": classes,
                "coef": classifier.coef_.tolist(),
                "intercept": classifier.intercept_.tolist(),
            }
        ),
        encoding="utf-8",
    )
    x, mask, y = splits["test"]
    return metrics(y, classifier.predict_proba(mean_features(x, mask)), classes)


def prepare(root, config, output):
    records, fingerprint, excluded = load_soccernet(root)
    (output / "dataset-audit.json").write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "excluded": excluded,
                "records": [asdict(r) for r in records],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    encoder = Encoder()
    splits = {}
    for split in ("train", "validation", "test"):
        selected = [r for r in records if r.split == split]
        if not selected:
            raise ValueError(f"Empty {split} split")
        x = np.zeros((len(selected), config["views"], config["frames"], 576), dtype=np.float32)
        mask = np.zeros((len(selected), config["views"]), dtype=bool)
        for i, record in enumerate(selected):
            for view, path in enumerate(record.views[: config["views"]]):
                try:
                    x[i, view] = cached_features(
                        path,
                        Path("artifacts/features"),
                        encoder,
                        fingerprint,
                        record.incident_id,
                        view,
                        config["frames"],
                        config["size"],
                    )
                except (ValueError, OSError) as exc:
                    raise ValueError(
                        f"Corrupt incident {record.incident_id}, view {view}; repair data before training"
                    ) from exc
                mask[i, view] = True
            if (i + 1) % 50 == 0 or i + 1 == len(selected):
                progress(output, "features", split=split, completed=i + 1, total=len(selected))
                print(
                    json.dumps(
                        {"feature_split": split, "completed": i + 1, "total": len(selected)}
                    ),
                    flush=True,
                )
        splits[split] = (x, mask, np.array([r.label for r in selected], dtype=np.int64))
    return splits, fingerprint, ACTION_CLASSES


def synthetic(config):
    rng = np.random.default_rng(config["seed"])
    splits = {}
    for split, count in (("train", 24), ("validation", 12), ("test", 12)):
        y = np.arange(count) % 3
        x = rng.normal(size=(count, 2, 8, 16)).astype(np.float32)
        x[:, :, :, 0] += y[:, None, None]
        mask = np.ones((count, 2), dtype=bool)
        mask[::3, 1] = False
        splits[split] = (x, mask, y)
    return splits, "synthetic-engineering-fixture-v1", ["synthetic-a", "synthetic-b", "synthetic-c"]


def main():
    global RUN_OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/smoke.json"))
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if not args.smoke and not args.dataset:
        parser.error("Real training requires --dataset pointing to authorized SoccerNet data")
    validate_config(config)
    seed_all(config["seed"])
    output = args.output or Path("artifacts/runs") / time.strftime("%Y%m%d-%H%M%S")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "model.pt").exists() and not args.resume:
        raise ValueError("Output contains a model; use a new directory or explicit --resume")
    RUN_OUTPUT = output
    progress(output, "starting")
    splits, fingerprint, classes = (
        synthetic(config) if args.smoke else prepare(args.dataset, config, output)
    )
    tracking = Path("artifacts/mlflow.sqlite").resolve()
    tracking.parent.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{tracking.as_posix()}")
    mlflow.set_experiment(
        "PitchSight engineering smoke" if args.smoke else "PitchSight MV-Foul action"
    )
    with mlflow.start_run() as run:
        mlflow.log_params(config | {"dataset_fingerprint": fingerprint, "synthetic": args.smoke})
        baseline_result = baseline(splits, classes, output)
        model, metadata, result = train_temporal(
            splits, config, output, classes, fingerprint, args.resume
        )
        manifest = {
            "schema_version": 1,
            "version": output.name,
            "model_type": "temporal-fusion",
            "checkpoint": "model.pt",
            "sha256": digest_file(output / "model.pt"),
            "architecture": metadata["architecture"],
            "classes": classes,
            "dataset_fingerprint": fingerprint,
            "provenance": "SYNTHETIC SMOKE TEST" if args.smoke else "AUTHORIZED LABELED DATA",
            "encoder": ENCODER,
            "preprocessing": PREPROCESSING,
            "frames": config["frames"],
            "size": config["size"],
            "views": config["views"],
            "temperature": result["temperature"],
            "calibration_split": "validation",
            "threshold": config["threshold"],
            "hardware": {
                "device": str(device()),
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "vram_bytes": torch.cuda.get_device_properties(0).total_memory
                if torch.cuda.is_available()
                else None,
            },
            "metrics_provenance": "test split; calibration/early stopping on validation",
            "run_id": run.info.run_id,
        }
        report = {
            "provenance": manifest["provenance"],
            "model_version": output.name,
            "run_id": run.info.run_id,
            "temporal": result,
            "baseline": baseline_result,
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        mlflow.log_metrics(
            {
                "test_accuracy": result["accuracy"],
                "test_macro_f1": result["report"]["macro avg"]["f1-score"],
                "baseline_test_accuracy": baseline_result["accuracy"],
                "classifier_ms_per_incident": result["classifier_ms_per_incident"],
            }
        )
        for name in ("metrics.json", "manifest.json", "baseline.json", "reliability.png"):
            mlflow.log_artifact(str(output / name))
        progress(output, "completed", run_id=run.info.run_id)
        print(
            json.dumps(
                {
                    "output": str(output),
                    "run_id": run.info.run_id,
                    "provenance": manifest["provenance"],
                    "device": str(device()),
                }
            )
        )


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        if RUN_OUTPUT is not None:
            progress(RUN_OUTPUT, "failed", detail="See local training log for the error")
        raise
