"""Decode untrusted media in a subprocess with a hard wall-clock timeout."""

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

MAX_BYTES = 100 * 1024 * 1024
MAX_DURATION = 120
EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}


def executable(name):
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
        for path in root.glob(f"Gyan.FFmpeg_*/ffmpeg-*/bin/{name}.exe"):
            return str(path)
    return None


def validate_header(path):
    with path.open("rb") as stream:
        header = stream.read(16)
    ext = path.suffix.lower()
    valid = (
        (ext in (".mp4", ".mov") and header[4:8] == b"ftyp")
        or (ext == ".avi" and header[:4] == b"RIFF" and header[8:12] == b"AVI ")
        or (ext == ".webm" and header[:4] == b"\x1aE\xdf\xa3")
    )
    if not valid:
        raise ValueError("Video extension and container signature do not match")


def decode(path: Path, output: Path, count=8, size=192):
    if not 1 <= count <= 64 or not 32 <= size <= 512:
        raise ValueError("Sampling settings outside safe bounds")
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        if not cap.isOpened() or not math.isfinite(fps) or fps <= 0 or frames <= 0:
            raise ValueError("Video cannot be decoded")
        duration = frames / fps
        if duration > MAX_DURATION or width * height > 3840 * 2160:
            raise ValueError("Video exceeds 120 seconds or 4K resolution cap")
        indices = np.linspace(0, frames - 1, count, dtype=int)
        sampled = []
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            ok, frame = cap.read()
            if not ok:
                raise ValueError("Video contains an undecodable sampled frame")
            sampled.append(cv2.cvtColor(cv2.resize(frame, (size, size)), cv2.COLOR_BGR2RGB))
        output.mkdir(parents=True, exist_ok=True)
        np.save(output / "frames.npy", np.stack(sampled), allow_pickle=False)
        cv2.imwrite(str(output / "thumbnail.jpg"), cv2.cvtColor(sampled[0], cv2.COLOR_RGB2BGR))
        return {
            "fps": fps,
            "frame_count": frames,
            "duration": duration,
            "width": width,
            "height": height,
            "sample_indices": indices.tolist(),
            "size": size,
            "samples": count,
        }
    finally:
        cap.release()


def process_video(path: Path, output: Path, count=8, size=192):
    if path.suffix.lower() not in EXTENSIONS or path.stat().st_size > MAX_BYTES:
        raise ValueError("Unsupported format or video exceeds 100 MiB")
    validate_header(path)
    command = [
        sys.executable,
        "-m",
        "pitchsight.video.processing",
        str(path.resolve()),
        str(output.resolve()),
        str(count),
        str(size),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    except subprocess.TimeoutExpired:
        raise ValueError("Video processing exceeded 45-second timeout") from None
    if result.returncode:
        raise ValueError("Video cannot be decoded or exceeds duration/resolution limits")
    return json.loads(result.stdout)


def browser_copy(path: Path, target: Path):
    ffmpeg = executable("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg unavailable; install FFmpeg for browser playback")
    args = [
        ffmpeg,
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        "scale='min(1280,iw)':-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(target),
    ]
    try:
        result = subprocess.run(args, capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        raise ValueError("Playback conversion timed out") from None
    if result.returncode:
        raise ValueError("Playback conversion failed")


if __name__ == "__main__":
    print(
        json.dumps(decode(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
    )
