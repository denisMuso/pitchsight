# Implementation status — 2026-11-06

Only executed checks count as evidence. Synthetic data validates engineering, not football performance.

| Milestone | Status | Evidence / remaining boundary |
|---|---|---|
| 0: native Windows bootstrap | DONE | Native toolchain/CUDA verified; private GitHub repository created and pushed |
| 1: match vertical slice | DONE in demo and live | Idempotent seed, typed HTTPX adapter, SQLite, FastAPI, React; browser verified LIVE API records; 380 PL + 144 CL matches and 56 standings synced |
| 2: video / human review | DONE for local engineering scope | Real decode/FFmpeg tests, multi-view grouping, review persistence, bounded jobs and recovery; browser upload completed |
| 3: training pipeline | DONE including first genuine run | Authorized MV-Foul, pretrained features, CUDA training and MLflow completed; further development uses validation only |
| 4: evaluation / inference | DONE engineering and first evaluation; model NOT ACTIVATED | Weak genuine test result audited; actual two-view inference matches saved probabilities; no active football model |
| 5: offside laboratory | DONE for position-only research scope | Direction, own half, level, uncertainty and homography tests; browser controls checked |
| 6: engineering / portfolio | DONE | Documentation, screenshot, locks and Windows CPU CI; remote workflow passed |

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
- CPU CI preflight: explicitly set `CUDA_VISIBLE_DEVICES=-1`, asserted CUDA unavailable, and completed smoke training on **cpu**, MLflow run **134e47bf552d43f0ba315e381628c7e2**. CI now uses `-1`; Windows PowerShell 5.1 removes environment variables assigned an empty string, which had left CUDA enabled in the first preflight attempt.
- Delivered run_backend.ps1 and run_frontend.ps1 launched in hidden PowerShell processes. Initially verified ok/demo and 8 demo matches. After authorized live sync, backend /health returns ok/live; live API contains 524 matches and the frontend displays LIVE API records.

## Browser evidence

- Dashboard displayed eight fictional records and provenance. [Actual screenshot](screenshots/overview.png) was captured and visually inspected.
- Created “Synthetic pipeline verification — not football evidence”, uploaded a generated 3-second AVI, saw `video · completed · 100%`, thumbnail and 8 sampled frames. Saved an INCONCLUSIVE human review with comments and audit timestamp.
- Embedded-browser playback was paused by its background-tab power policy. Independent real FFmpeg conversion and decoded MP4 tests pass; continuous visible playback is not claimed from that attempt.
- Model Lab displayed recorded smoke metrics/loss history with a synthetic-only warning while the registry remained unavailable.
- Offside controls changed OFFSIDE POSITION at x=77 to INCONCLUSIVE at x=74.1 with ±0.25 m uncertainty; interval -0.40 to 0.60 m. Homography fitting returned a near-zero residual and its explicit accuracy limitation.
- Current IFAB Law 11 and SoccerNet pages inspected in browser; official MV-Foul loader/classes and football-data.org docs retrieved directly.

## Remaining external actions and limitations

GitHub authorization completed for denisMuso. [Repository](https://github.com/denisMuso/pitchsight) was created with private visibility (verified with gh), main pushed and upstream configured, with zero ahead/behind commits. [Initial remote CI](https://github.com/denisMuso/pitchsight/actions/runs/41879942060) passed installation, Python lint/tests, CPU smoke training and frontend checks on Windows.

Live provider access verified on 2026-11-04: both PL and CL match and standings syncs completed. API counts: 380 PL matches, 144 CL matches, 56 standings rows. Local mode switched to live, backend restarted and browser verified LIVE API provenance. The dashboard paginates all matches in groups of 25 and displays the filtered total. Browser verified next-page navigation (26-50 of 524) and filter reset (1-25 of 144 CL matches, Previous disabled). Frontend tests (3) and production build passed after this change. The token remains in ignored `.env`; it was not printed or committed.

SoccerNet NDA access obtained. The official SoccerNet 0.2.0 downloader fetched 224p archives from its Hugging Face mirror (3,076,168,763 bytes). The supplied password decrypted them. Audit: 2,853 train / 404 validation / 300 test incidents, 71 excluded unknown labels, all eight classes present, exact-content leakage checks passed. The first genuine GPU run completed under artifacts/runs/mvfoul-rtx3060-first: test accuracy 21.33%, macro F1 0.1230; 299/300 abstentions at threshold 0.65. It was not activated. See first-football-experiment.md for the fixed audit and limitations. Live progress and local logs are available. No football model is registered yet.

ML-focused improvements: saved training preflight (configuration, disk/VRAM, labels/splits, memory estimate); live run progress; per-class metrics/confusion matrices/calibration summaries; shared video controls with session-local manual offsets; JSON review export; metadata refresh with one-minute cooldown; keyboard focus styling and responsive tables. Browser verified the saved preflight and per-class tables and two synthetic review views. Shared playback is approximate and is not evidence of camera synchronization accuracy.

Additional browser checks: shared seek set both videos to 1.0s; a 0.5s second-view offset produced times 1.2s and 1.7s. Mobile Model Lab with the dataset audit expanded has no horizontal page overflow after wrapping the fingerprint. Native download completion for review export could not be observed in the embedded browser. Model Lab is now the initial workspace.

Latest validation: Ruff passed; 37 Python tests passed (20.29s), 3 frontend tests passed, TypeScript/Vite build passed (22 modules). CPU smoke run d8a65aae5cf44b45bbee37eb5a0c0137 completed both epochs and wrote progress stage completed. Data extraction tests use encrypted fixtures, wrong-password rejection and unsafe-path rejection. These checks do not establish football-model performance.

The local app has no multi-user authentication and runs one worker/process. It is not publicly deployed. The classifier implements action labels, not a severity head. Geometry determines position only. Content hashes cannot detect all semantically duplicated incidents. See the data/model cards, security and offside notes.

## First genuine evaluation and development controls

The first run completed eight epochs; the fixed audit reproduced both temporal and
logistic test confusion matrices exactly. An isolated registry processed two real
views and reproduced audit probabilities within 1e-5. It returned INCONCLUSIVE and
did not change the active app registry. See [experiment report](first-football-experiment.md).

Added paired-bootstrap accuracy comparisons, fixed-threshold coverage/accepted
accuracy, per-incident error records and validation-only missing-view ablation.
Standardized logistic regression fits scaling on training data only and records
convergence. Validation-only development skips test feature extraction/evaluation
and is explicitly rejected by the model registry. Reports and the UI distinguish
development validation scores from held-out test scores.

Verification on 2026-11-06: 40 Python tests passed in 33.44s, 3 frontend tests passed,
TypeScript/Vite build passed, Ruff passed. CPU validation-only CLI smoke run
b5f46804c69a4bf9864a2e00447fd234 completed, saved baseline metrics and validation
provenance. Browser verified the fixed-threshold audit (1 accepted / 299 inconclusive)
and MODEL UNAVAILABLE status. The evaluation figure was rendered and visually checked.

Validation-only run mvfoul-validation-lr3e4 completed 13 epochs on CUDA (MLflow
19c92dd300cf4c48bce269f57f1006c8): accuracy 37.62%, macro F1 0.1917 on validation;
standardized logistic baseline accuracy 26.73%, macro F1 0.1650, converged after
284 iterations. Best validation loss 1.63876. Test was not reevaluated. The actual
development manifest was rejected by the registry and no active registry file exists.
