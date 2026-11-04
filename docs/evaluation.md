# Evaluation protocol

Keep all views of an incident in its official split. Train optimizer and baseline on train only; select the temporal checkpoint and fit one scalar temperature on validation only. Evaluate test after those choices are fixed. Never tune a threshold on the test report. Running many experiments and selecting on test results would still create leakage; the code cannot prevent that research practice.

Reports include accuracy, balanced accuracy, per-class precision/recall/F1/support, macro/weighted summaries, confusion matrix, class distribution, error indices, train/validation loss history, classifier milliseconds per incident, device and peak CUDA allocation. Error indices map to the split order in the local dataset audit. Full pipeline latency is not inferred from classifier timing.

Calibration writes validation confidence/accuracy bins, expected calibration error and a reliability PNG. Softmax confidence is labeled uncalibrated unless validation temperature metadata is present. A calibrated score is still an estimate whose validity depends on the population and validation sample. It is not an official probability that a foul occurred.

Executed smoke run: `artifacts/runs/smoke-verified`, MLflow run `e6ffab838b2046b9b2ae7c20e77ecc2d`, CUDA, two epochs, synthetic-only. Local MLflow uses artifacts/mlflow.sqlite; no tracking server is required. The Model Lab reads recorded metrics files and keeps smoke provenance prominent. Football metrics remain unavailable.

Unit tests use known perfect-classification fixtures, leakage duplicates, missing-view gradients, reload equivalence and forbidden test calibration. Synthetic experiments and unit tests do not establish sporting validity.
