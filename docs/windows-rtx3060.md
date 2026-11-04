# Windows / RTX 3060

Verified machine: Windows 11, Python 3.12.10, PowerShell 5.1, Node 22.21.1, RTX 3060 with 12,288 MiB VRAM, NVIDIA driver 617.42. Doctor reported 482 GB free during setup. This is a measured 12 GB card; no assumption was made from the model name.

The official [PyTorch selector](https://pytorch.org/get-started/locally/) was retrieved during implementation. It advertised stable 2.15.0 and Windows CUDA 13.2/13.4 wheels. Installed and verified: torch 2.15.0+cu132 and torchvision 0.29.2+cu132. CUDA available=True; GPU tensor `(ones(8)*2).sum()` returned 16.0. A two-epoch GRU smoke run and pretrained MobileNet feature extraction both ran on CUDA.

```powershell
winget install --id GitHub.cli --exact
winget install --id Gyan.FFmpeg --exact
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu132
.\.venv\Scripts\python.exe -m pip install -e '.[dev,ml]'
```

Open a new terminal after winget installation to refresh PATH. Video processing also discovers the standard winget FFmpeg package path. No CUDA Toolkit installation is required. On another GPU/driver, use the official selector; do not assume this wheel choice applies indefinitely.

The conservative RTX config uses 160 px, 8 frames/view, 2 views, batch 4, accumulation 4, hidden size 64, zero DataLoader workers. Frozen encoder features are cached. Device selection is CUDA → MPS → CPU; AMP is CUDA-only. The actual smoke run records peak CUDA allocation and classifier latency in its metrics file. Those measurements exclude video decoding/encoder time and are not production capacity claims. Profile representative authorized clips before increasing resolution, batch size or view count.

If CUDA fails, install CPU wheels and continue API/CPU tests. Avoid running long training alongside GPU-heavy desktop apps. Resume must use the same config, dataset fingerprint, class order and output directory containing the original best checkpoint.
