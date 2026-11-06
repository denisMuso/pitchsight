# ML research workflow

## Authorized data

Install optional acquisition dependencies with `python -m pip install -e ".[data]"`.
The SoccerNet 0.2.0 downloader uses the official Hugging Face mirror. The legacy
OwnCloud endpoint returned HTTP 401 with the supplied NDA credential; the official
mirror archives were accessible and the supplied password decrypted them.

```python
from SoccerNet.Downloader import SoccerNetDownloader
SoccerNetDownloader(LocalDirectory="data/soccernet").downloadDataTask(
    task="mvfouls", split=["train", "valid", "test"], version="224p", source="HuggingFace"
)
```

Save `SOCCERNET_PASSWORD` in ignored `.env`, then run:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_soccernet.py
.\.venv\Scripts\python.exe -m pitchsight.training.preflight --dataset data/soccernet/mvfouls
```

Extraction checks paths and available disk before decrypting to Train/Valid/Test.
Preflight checks configuration, hardware, disk, official labels, content hashes and
split separation without training. It reports exclusions, class counts, view
truncation and approximate feature memory. Video decoding is checked during feature
extraction, not preflight. A ready report does not guarantee sufficient GPU memory.
The Model Lab displays the saved report with its timestamp; rerun it after changes.

## First experiment

Use the fixed RTX 3060 configuration: two views, eight frames, frozen ImageNet
MobileNetV3 features, class-weighted logistic regression baseline and temporal GRU
with learned view attention. Batch size four, accumulation four, up to 30 epochs
with validation early stopping. Use a fresh output directory for each experiment.

```powershell
.\scripts\train_windows.ps1 -Dataset data/soccernet/mvfouls -Config configs/rtx3060.json -Output artifacts/runs/mvfoul-rtx3060-first
```

Record this initial configuration before looking at test metrics. Do not choose
later configurations based on test scores. The initial threshold is 0.65, not a
threshold selected to meet an officiating performance target. Compare experiments
on validation data; reserve an independent final evaluation for any selected model.

The local audit contains 2,853 train / 404 validation / 300 test usable incidents,
71 excluded unknown labels, and all eight action classes. Validation has only one
Dive example; class-specific conclusions require caution. Two-view training
truncates 658 train / 119 validation / 89 test incidents with additional views.
Content hashing detects exact duplicates, not semantic overlap or shared games.

## Reviewing evidence

Model Lab exposes per-class test metrics, macro F1, a confusion matrix, learning
history and validation calibration summary. Synthetic reports stay explicitly
labeled. Classifier latency excludes decoding and feature extraction.

Incident Review supports shared play/pause/seek and per-view clip-time offsets.
Alignment is session-local and approximate; replay speed differences require
manual review. Export review JSON to retain the incident metadata, jobs, human
decisions and model results without copying footage. Local playback URLs in exports
refer to this installation. Offsets are not part of that export.

System/About shows sync timestamps and a refresh action with a per-process
one-minute cooldown. Each competition has its own completed or partial status.

## Walkthrough

1. Show Model Lab's dataset audit and explain what has and has not been checked.
2. Explain the frozen visual encoder, temporal pooling and masked view fusion.
3. Compare the baseline and temporal report; inspect minority-class performance.
4. Explain validation-only calibration and why confidence is not a referee verdict.
5. Open an authorized incident, align camera views and save an independent review.
6. Export the review. Keep dataset archives, credentials and checkpoints local.

## Development after the first evaluation

The [first football result](first-football-experiment.md) is weak and remains inactive.
Use validation-only runs for further development:

```powershell
.\scripts\train_windows.ps1 -Dataset data/soccernet/mvfouls -ValidationOnly -Config configs/rtx3060-validation.json -Output artifacts/runs/new-development-run
```

This mode does not extract or evaluate test features. Validation is also used for
early stopping and temperature fitting, so development metrics are optimistic relative
to independent evaluation. The registry rejects these manifests. The standardized
logistic baseline fits its scaler on train only and exports equivalent coefficients in
raw feature space, plus iteration count and convergence status. New runs save baseline
metrics before temporal training starts. Test results from the first run are retained.
