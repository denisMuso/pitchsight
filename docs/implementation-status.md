# Implementation status

Only executed checks count as evidence. Synthetic data is for engineering validation, never football performance.

## Milestone 0 — PARTIAL (GitHub authorization)
- Python 3.12.10, PowerShell 5.1, Node 22.21.1, npm 11.11.0, local Git main initialized.
- NVIDIA RTX 3060: 12,288 MiB, driver 617.42 (nvidia-smi).
- GitHub CLI 2.103.3 and FFmpeg 9.0.2 installed through winget.
- Virtual environment and core dependencies installed. Sandbox blocked pip and pytest temporary files; elevated reruns succeeded.
- GitHub device authorization pending.
- Official PyTorch selector retrieved: stable Windows CUDA 13.2 wheels. Installed torch 2.15.0+cu132, torchvision 0.29.2+cu132.
- `python scripts/doctor.py`: CUDA available, RTX 3060, 12.0 GiB, CUDA tensor sum = 16.0; Windows 11, 482 GB disk free.

## Milestone 1 — DONE (demo vertical slice); live verification BLOCKED — API TOKEN
- Implemented SQLAlchemy entities, demo seeding, HTTPX adapter, sync CLI, FastAPI match endpoints and React dashboard.
- `.venv\Scripts\python.exe -m pytest -q`: **4 passed** (API/idempotency/live isolation/provider retry).
- Ruff check passed. `npm.cmd run build`: TypeScript + Vite 8.3.5 passed. `npm.cmd test`: 1 passed (Vitest 5.1.0). Updated initially vulnerable tooling; npm audit reports 0 vulnerabilities.
- Browser opened http://127.0.0.1:5173 and verified all 8 match records from running FastAPI at http://127.0.0.1:8000, with DEMO DATA labels and two competitions.

## Milestones 2–6 — IN PROGRESS
- Not yet verified. No trained football model or football metrics claimed.
- Real training: **BLOCKED — DATASET ACCESS**. Official MV-Foul README requires NDA/password for videos and annotations.
