# Implementation status — 2026-11-04

Only executed checks count as evidence. Synthetic data validates engineering, not football performance.

| Milestone | Status | Evidence / remaining boundary |
|---|---|---|
| 0: native Windows bootstrap | DONE locally; GitHub BLOCKED — AUTHORIZATION | Python 3.12 venv, scripts, Git main, FFmpeg and CUDA verified |
| 1: match vertical slice | DONE in demo; live verification BLOCKED — API TOKEN | Idempotent seed, typed HTTPX adapter, SQLite, FastAPI, React; browser displayed 8 fictional matches |
| 2: video / human review | DONE for local engineering scope | Real decode/FFmpeg tests, multi-view grouping, review persistence, bounded jobs and recovery; browser upload completed |
| 3: training pipeline | DONE implementation/smoke; football training BLOCKED — DATASET ACCESS | Official action schema, pretrained features, baseline, temporal/fusion model, AMP, resume and MLflow; two CUDA smoke runs |
| 4: evaluation / inference | DONE implementation/tests; football validation BLOCKED — DATASET ACCESS | Metrics, validation calibration, checkpoint gates, inference and unavailable-model API; no football model registered |
| 5: offside laboratory | DONE for position-only research scope | Direction, own half, level, uncertainty and homography tests; browser controls checked |
| 6: engineering / portfolio | DONE locally; remote CI BLOCKED — GITHUB AUTHORIZATION | Documentation, captured screenshot, locks and CPU Windows CI definition; remote CI not claimed |

## Final executed verification

`powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1`

- Ruff: **all checks passed**.
- pytest: **29 passed**, 23.30 seconds in the final run.
- Vitest 5.1.0: **3 passed**.
- TypeScript and Vite 8.3.5 production build: **passed**, 21 modules transformed.
- One upstream Starlette TestClient deprecation warning recommends httpx2; the locked HTTPX tests still pass.
- `pip check`: no broken requirements. `npm ci` audit: **0 vulnerabilities**.

Tests cover provider retries, denied standings, idempotent live fixture upserts, missing-token logging, demo/live isolation, corrupt/oversized uploads, actual FFmpeg conversion, grouped views, reviews, queue limits/recovery, origin/body-size guards, official annotation fixtures/content leakage, both fusion modes, missing-view gradients, reload/resume equivalence, calibration rules, registry hash/path/provenance gates and checkpoint inference with fixture embeddings. No protected dataset is used by tests.

## Hardware and scripts

- Windows 11; PowerShell 5.1; Python 3.12.10; Node 22.21.1; npm 11.11.0.
- NVIDIA RTX 3060: **12,288 MiB**, driver **617.42**. Official PyTorch Windows selector inspected before wheel selection.
- torch **2.15.0+cu132**, torchvision **0.29.2+cu132**. CUDA available; GPU tensor sum **16.0**. Pretrained MobileNet produced finite features of shape **(2, 576)** on CUDA.
- GitHub CLI **2.103.3**, FFmpeg **9.0.2** installed with winget; doctor discovers both. Free disk was 482.5 GB on recheck.
- `powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1 -ML`: **exit 0**, dependencies, npm ci, demo seed and doctor succeeded.
- `powershell -ExecutionPolicy Bypass -File scripts/train_windows.ps1 -Smoke -Output artifacts/runs/smoke-script-verified`: **exit 0**, two-epoch CUDA run **800f83ddc53042a5aac3b6bd2f0b8be4** logged to local MLflow.
- Earlier direct smoke run **e6ffab838b2046b9b2ae7c20e77ecc2d** remains under artifacts/runs/smoke-verified. Both are SYNTHETIC SMOKE TEST and cannot serve football predictions.
- Delivered run_backend.ps1 and run_frontend.ps1 launched in hidden PowerShell processes. Backend /health returns ok/demo; frontend HTTP 200; frontend API proxy returns 8 matches.

## Browser evidence

- Dashboard displayed eight fictional records and provenance. [Actual screenshot](screenshots/overview.png) was captured and visually inspected.
- Created “Synthetic pipeline verification — not football evidence”, uploaded a generated 3-second AVI, saw `video · completed · 100%`, thumbnail and 8 sampled frames. Saved an INCONCLUSIVE human review with comments and audit timestamp.
- Embedded-browser playback was paused by its background-tab power policy. Independent real FFmpeg conversion and decoded MP4 tests pass; continuous visible playback is not claimed from that attempt.
- Model Lab displayed recorded smoke metrics/loss history with a synthetic-only warning while the registry remained unavailable.
- Offside controls changed OFFSIDE POSITION at x=77 to INCONCLUSIVE at x=74.1 with ±0.25 m uncertainty; interval -0.40 to 0.60 m. Homography fitting returned a near-zero residual and its explicit accuracy limitation.
- Current IFAB Law 11 and SoccerNet pages inspected in browser; official MV-Foul loader/classes and football-data.org docs retrieved directly.

## Remaining external actions and limitations

1. Complete GitHub browser authorization to create/push the private `pitchsight` repository. A device-login flow was initiated and restarted after interruption. No remote push, public repository or remote CI result is claimed.
2. Add a football-data.org token to local `.env` for live metadata; endpoint access depends on the provider plan. The user's account has not been tested.
3. Obtain SoccerNet NDA/password authorization and place extracted Train/Valid/Test files locally for genuine training. No hours-long training or large dataset download was started.

The local app has no multi-user authentication and runs one worker/process. It is not publicly deployed. The classifier implements action labels, not a severity head. Geometry determines position only. Content hashes cannot detect all semantically duplicated incidents. See the data/model cards, security and offside notes.
