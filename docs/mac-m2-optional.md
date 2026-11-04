# Optional Mac M2 portability

Windows is the primary verified platform. Mac setup has not been executed. Python uses pathlib and no hardcoded CUDA calls; inference/training selects MPS only when CUDA is unavailable and MPS is supported.

On an authorized future Mac setup, install Python 3.12, Node LTS and FFmpeg natively, create a venv, install the project and standard macOS PyTorch/torchvision wheels from the official selector. Invoke Python modules directly; PowerShell convenience scripts target Windows. Use 160 px, 8 frames, one or two views, small batches and num_workers=0 on 8 GB RAM. MPS does not use the CUDA AMP path. Do not copy a Windows venv onto macOS. Portable checkpoints use CPU tensors and explicit map_location.

No Mac installation, remote machine or cloud GPU is required for the Windows application.
