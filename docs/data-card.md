# Data card

## Included engineering data
Eight deterministic fictional fixtures across PL/CL-named competitions and four fictional teams. All rows say DEMO DATA. These are not real matches, standings, incidents or results. Generated grayscale/text videos and random tensors are engineering fixtures only; they carry no football labels or performance meaning.

## Authorized MV-Foul adapter
Expected local folders: Train, Valid and Test, each with annotations.json and action directories. Challenge is excluded because labels are unavailable. Only action classes published in the official schema are supported: Tackling, Standing tackling, High leg, Holding, Pushing, Elbowing, Challenge, Dive. Empty/“Dont know” action labels are excluded with audit reasons; other unknown labels fail loudly. Offence and Severity fields are not used to infer extra heads.

Incident IDs are namespaced by official split because local numeric IDs restart. SHA-256 clip hashes detect identical content reused across incidents/splits. The fingerprint covers normalized incident metadata, class labels and content hashes. This catches exact duplication, not semantically repeated incidents encoded differently; dataset-level manual audit remains necessary. Official splits are retained, not randomly split by view. Corrupt sampled clips abort training with the incident/view identified; there is no silent omission from evaluation.

Authorized MV-Foul 224p data is now downloaded and decrypted locally. The audited usable splits contain 2,853 train, 404 validation and 300 test incidents; 71 unknown-label incidents were excluded. All eight classes are present; validation contains only one Dive example. Exact-content leakage checks passed. The local NDA governs use; no dataset is committed. Broadcast bias, camera selection, ambiguous labels, class imbalance and match-level correlations limit generalization. Human reviews are append-only local observations, not automatically promoted to training ground truth.
