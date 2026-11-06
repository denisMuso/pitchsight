# Model card

Status: **First genuine model trained and audited; not activated because performance is poor.**

Implemented model: frozen torchvision MobileNetV3-Small ImageNet features (576 dimensions per frame), temporal GRU with attention pooling, then masked mean or learned attention across camera views. The classification head uses the authorized dataset's eight action classes. There is no invented severity head. Logistic regression on pooled features is the reproducible baseline; its parameters export as numeric JSON, not pickle.

Engineering smoke model: three synthetic labels, random tensors, two epochs, CUDA. It verifies optimizer/backprop/checkpoint/evaluation/logging, not foul recognition. The registry explicitly refuses smoke provenance. Do not cite its accuracy as football performance.

Training uses class-weighted loss, seeded shuffling, AdamW, CUDA AMP when supported, gradient accumulation, validation early stopping and resume metadata checks. Validation temperature scaling precedes a held-out test evaluation. The configurable abstention threshold defaults to 0.65 and is a research policy, not a validated referee threshold. Low scores return INCONCLUSIVE; successful scores identify an action class, not whether an offence legally occurred.

Manifests bind architecture, labels, encoder/preprocessing, data fingerprint, hardware, hash, checkpoint, MLflow run and metric provenance. Only explicit local registration of trusted artifacts is supported. Hashing detects accidental replacement; it is not a digital signature or proof of lawful data provenance. Manifest provenance is a trusted local operator assertion. Use weights_only loading; never accept arbitrary model uploads.

First held-out result: 21.33% accuracy, 0.1230 macro F1 on 300 incidents; at threshold 0.65, 299 abstentions and one incorrect accepted prediction. The original logistic baseline achieved 25.00% accuracy but hit its iteration limit. See [experiment report](first-football-experiment.md). The real-video inference path matches the independent audit; this is engineering verification, not evidence of usefulness. Validation-only development runs cannot be registered.

Not suitable for automatic officiating, disciplinary decisions, player judgments, high-stakes betting or claims of professional VAR precision. Camera synchronization, event timing, class ambiguity and out-of-domain footage can invalidate predictions. No deployment performance is established.
