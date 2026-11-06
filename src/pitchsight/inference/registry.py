import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pitchsight.ml.dataset import digest_file


class ModelUnavailable(ValueError):
    pass


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    version: str
    model_type: str
    checkpoint: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    architecture: dict[str, int | str]
    classes: list[str] = Field(min_length=2)
    dataset_fingerprint: str
    provenance: str
    encoder: str
    preprocessing: str
    frames: int = Field(ge=1, le=64)
    size: int = Field(ge=32, le=512)
    views: int = Field(ge=1, le=8)
    temperature: float = Field(gt=0, le=10, allow_inf_nan=False)
    calibration_split: str
    threshold: float = Field(ge=0, le=1, allow_inf_nan=False)
    hardware: dict
    metrics_provenance: str
    run_id: str


def read_manifest(path: Path):
    try:
        manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError):
        raise ModelUnavailable("MODEL UNAVAILABLE: missing or invalid manifest") from None
    if manifest.schema_version != 1 or manifest.model_type != "temporal-fusion":
        raise ModelUnavailable("MODEL UNAVAILABLE: incompatible schema/model type")
    if manifest.provenance != "AUTHORIZED LABELED DATA":
        raise ModelUnavailable(
            "MODEL UNAVAILABLE: synthetic runs cannot serve football predictions"
        )
    if manifest.metrics_provenance.startswith("validation-only"):
        raise ModelUnavailable("MODEL UNAVAILABLE: development-only run has no held-out evaluation")
    if (
        manifest.encoder != "mobilenet_v3_small-IMAGENET1K_V1"
        or manifest.preprocessing != "rgb-square-imagenet-normalization-v1"
    ):
        raise ModelUnavailable("MODEL UNAVAILABLE: incompatible preprocessing")
    architecture = manifest.architecture
    if (
        architecture.get("features") != 576
        or architecture.get("classes") != len(manifest.classes)
        or architecture.get("fusion") not in ("mean", "attention")
        or not isinstance(architecture.get("hidden"), int)
        or not 1 <= architecture["hidden"] <= 512
    ):
        raise ModelUnavailable("MODEL UNAVAILABLE: incompatible architecture")
    if (
        len(set(manifest.classes)) != len(manifest.classes)
        or manifest.calibration_split != "validation"
    ):
        raise ModelUnavailable("MODEL UNAVAILABLE: invalid classes/calibration provenance")
    checkpoint = (path.parent / manifest.checkpoint).resolve()
    if (
        not checkpoint.is_relative_to(path.parent.resolve())
        or not checkpoint.is_file()
        or digest_file(checkpoint) != manifest.sha256
    ):
        raise ModelUnavailable("MODEL UNAVAILABLE: missing, unsafe, or changed checkpoint")
    return manifest, checkpoint


def active_manifest(root=Path("artifacts")):
    try:
        active = json.loads((root / "registry/active.json").read_text())
        path = (root / active["manifest"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ModelUnavailable("MODEL UNAVAILABLE: no valid local model registered") from None
    manifest, checkpoint = read_manifest(path)
    return manifest, checkpoint


def register(path: Path, root=Path("artifacts")):
    path, root = path.resolve(), root.resolve()
    if not path.is_relative_to(root):
        raise ModelUnavailable("Registry accepts only trusted models inside artifacts")
    read_manifest(path)
    registry = root / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    temp = registry / "active.tmp"
    temp.write_text(json.dumps({"manifest": path.relative_to(root).as_posix()}), encoding="utf-8")
    temp.replace(registry / "active.json")


def predict(paths, root=Path("artifacts")):
    import numpy as np
    import torch

    from pitchsight.evaluation.metrics import decision
    from pitchsight.ml.features import Encoder, cached_features
    from pitchsight.ml.models import TemporalFusion, device

    manifest, checkpoint = active_manifest(root)
    if not paths:
        raise ValueError("Upload at least one authorized view before analysis")
    target = device()
    try:
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if (
            saved["metadata"]["classes"] != manifest.classes
            or saved["metadata"]["fingerprint"] != manifest.dataset_fingerprint
        ):
            raise ValueError("Checkpoint metadata mismatch")
        model = TemporalFusion(**manifest.architecture).to(target)
        model.load_state_dict(saved["state_dict"], strict=True)
        model.eval()
    except Exception as exc:
        raise ModelUnavailable("MODEL UNAVAILABLE: incompatible checkpoint") from exc
    encoder = Encoder(target)
    values = np.zeros((1, manifest.views, manifest.frames, 576), dtype=np.float32)
    mask = np.zeros((1, manifest.views), dtype=bool)
    for i, path in enumerate(paths[: manifest.views]):
        values[0, i] = cached_features(
            path,
            root / "features",
            encoder,
            manifest.dataset_fingerprint,
            "inference",
            i,
            manifest.frames,
            manifest.size,
        )
        mask[0, i] = True
    with torch.inference_mode():
        logits = model(torch.tensor(values, device=target), torch.tensor(mask, device=target))
        probabilities = (logits / manifest.temperature).softmax(dim=1)[0].cpu().numpy()
    result = decision(probabilities, manifest.classes, manifest.threshold, calibrated=True)
    result.update(
        {"model_version": manifest.version, "views_used": int(mask.sum()), "research_only": True}
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Register a trusted local trained model (no uploads)"
    )
    parser.add_argument("manifest", type=Path)
    register(parser.parse_args().manifest)
    print("Registered trusted local model")
