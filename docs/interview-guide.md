# Portfolio discussion guide

**What did you build?** A native local research application with an actual API-to-database-to-React slice, authorized media processing, human review, executable ML training and an independent geometry lab.

**Why SQLite and a local worker?** The target is one Windows desktop and a zero-cost budget. Foreign keys, WAL, short transactions and bounded admission solve the current scope without distributed infrastructure. Restart marks unfinished jobs failed explicitly. Multiple server processes are outside the design.

**How is evaluation kept honest?** Incident-level official splits, duplicate-content detection, validation-only early stopping/calibration, held-out evaluation and explicit provenance. Demo metadata, generated videos and random tensor tests never become football metrics. A smoke manifest cannot be registered for inference.

**How does the model use multiple cameras?** A frozen ImageNet encoder produces frame features; a GRU and temporal attention produce per-view representations. Masked mean/attention fusion combines available views. Missing views receive zero influence; an all-missing incident is rejected. The baseline pools the same features into logistic regression.

**What was measured on the hardware?** The RTX 3060 has 12 GB VRAM; a CUDA tensor operation, pretrained feature extraction and two-epoch synthetic training ran successfully. Real football training remains blocked on authorized labeled data. Do not present smoke accuracy as a model-quality achievement.

**What would you improve next?** Authorized-data evaluation; match-level leakage audit; camera synchronization; authenticated reviewers and retention policy; full pipeline performance profiling; schema migrations; independent calibration validation; robust monitoring. Add complexity only when measurements justify it.

**What is the offside lab's claim?** Position-only educational math with uncertainty. It cannot recover 3D body points or exact contact timing from arbitrary broadcast video, and it never adjudicates an offence.
