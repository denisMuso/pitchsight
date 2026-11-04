"""Portable diagnostics, with no installation or credential disclosure."""
import importlib.util
import json
import platform
import shutil
import subprocess


def diagnose():
    result = {"os": platform.platform(), "python": platform.python_version(), "disk_free_gb": round(shutil.disk_usage('.').free / 1024**3, 1)}
    for tool in ("git", "gh", "node", "npm", "ffmpeg", "ffprobe", "nvidia-smi"):
        result[tool] = shutil.which(tool)
    if shutil.which("nvidia-smi"):
        result["gpu_driver"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=15).stdout.strip()
    if importlib.util.find_spec("torch"):
        import torch
        result["torch"] = torch.__version__
        result["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            result["gpu"] = torch.cuda.get_device_name(0)
            result["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            result["cuda_tensor_result"] = (torch.ones(8, device="cuda") * 2).sum().item()
    return result


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2))
