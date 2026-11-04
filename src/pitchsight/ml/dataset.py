"""Adapter for the official sn-mvfoul Actions/Clips annotation structure.

Uses the original Action class head only; no inferred severity or relabeling.
Source: SoccerNet/sn-mvfoul, VARS model/data_loader.py and config/classes.py.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ACTION_CLASSES = [
    "Tackling",
    "Standing tackling",
    "High leg",
    "Holding",
    "Pushing",
    "Elbowing",
    "Challenge",
    "Dive",
]
SPLITS = {"Train": "train", "Valid": "validation", "Test": "test"}


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class Record:
    incident_id: str
    split: str
    label: int
    views: list[str]
    hashes: list[str]


def validate_splits(records):
    seen_ids, seen_hashes = {}, {}
    for record in records:
        if record.split not in SPLITS.values():
            raise ValueError("Unsupported split; challenge has no labels")
        if record.incident_id in seen_ids:
            raise ValueError("Duplicate incident / split leakage")
        seen_ids[record.incident_id] = record.split
        if not record.views or len(record.views) != len(record.hashes):
            raise ValueError("Incident must contain verified views")
        for digest in record.hashes:
            if digest in seen_hashes and seen_hashes[digest] != record.incident_id:
                raise ValueError("Duplicate video content across incidents / split leakage")
            seen_hashes[digest] = record.incident_id


def load_soccernet(root: Path):
    root = root.resolve()
    records, excluded = [], []
    for directory, split in SPLITS.items():
        annotation = root / directory / "annotations.json"
        if not annotation.is_file():
            raise ValueError(f"DATASET ACCESS: missing authorized {directory}/annotations.json")
        payload = json.loads(annotation.read_text(encoding="utf-8"))
        actions = payload.get("Actions")
        if not isinstance(actions, dict):
            raise ValueError("Expected official Actions object")
        for action_id, action in actions.items():
            if not str(action_id).isdigit():
                raise ValueError("Invalid action identifier")
            label = action.get("Action class")
            if label in ("", "Dont know"):
                excluded.append(
                    {"incident": f"{directory}/{action_id}", "reason": "Unknown action class"}
                )
                continue
            if label not in ACTION_CLASSES:
                raise ValueError(f"Unsupported dataset action label: {label}")
            clips = action.get("Clips")
            if not isinstance(clips, (list, dict)) or not clips:
                raise ValueError("Missing Clips metadata")
            # Original IDs restart at zero within each split; namespace them.
            folder = root / directory / f"action_{action_id}"
            views = [folder / f"clip_{i}.mp4" for i in range(len(clips))]
            if any(not path.is_file() or not path.resolve().is_relative_to(root) for path in views):
                raise ValueError(f"Missing or unsafe clip for {directory}/{action_id}")
            records.append(
                Record(
                    f"{directory}/{action_id}",
                    split,
                    ACTION_CLASSES.index(label),
                    [str(p.resolve()) for p in views],
                    [digest_file(p) for p in views],
                )
            )
    validate_splits(records)
    fingerprint = hashlib.sha256(
        json.dumps(
            [{**asdict(r), "views": [Path(v).name for v in r.views]} for r in records],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return records, fingerprint, excluded
