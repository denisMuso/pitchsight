import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import torch
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from pitchsight.ml.dataset import digest_file
from pitchsight.ml.models import device
from pitchsight.video.processing import process_video

ENCODER = "mobilenet_v3_small-IMAGENET1K_V1"
PREPROCESSING = "rgb-square-imagenet-normalization-v1"


class Encoder:
    def __init__(self, target=None):
        torch.hub.set_dir(str(Path("artifacts/torch-cache").resolve()))
        self.device = target or device()
        self.model = (
            mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
            .features.to(self.device)
            .eval()
        )
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)

    @torch.inference_mode()
    def encode(self, frames):
        x = torch.from_numpy(frames.copy()).permute(0, 3, 1, 2).float().to(self.device) / 255
        mean = x.new_tensor([0.485, 0.456, 0.406])[None, :, None, None]
        std = x.new_tensor([0.229, 0.224, 0.225])[None, :, None, None]
        return self.model((x - mean) / std).mean(dim=(-1, -2)).cpu().numpy()


def cached_features(path, cache, encoder, fingerprint, incident, view, frames=8, size=160):
    settings = {
        "encoder": ENCODER,
        "preprocessing": PREPROCESSING,
        "fingerprint": fingerprint,
        "incident": incident,
        "view": view,
        "sha256": digest_file(path),
        "frames": frames,
        "size": size,
    }
    key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{key}.npy"
    if target.exists():
        values = np.load(target, allow_pickle=False)
        if values.shape == (frames, 576) and np.isfinite(values).all():
            return values
        target.unlink()
    with tempfile.TemporaryDirectory(prefix="frames-", dir=cache) as temporary:
        output = Path(temporary)
        process_video(Path(path), output, frames, size)
        values = encoder.encode(np.load(output / "frames.npy", allow_pickle=False))
    if values.shape != (frames, 576) or not np.isfinite(values).all():
        raise ValueError("Unexpected visual features")
    temporary = target.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        np.save(stream, values, allow_pickle=False)
    temporary.replace(target)
    return values
