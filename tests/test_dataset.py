import json

import pytest

from pitchsight.ml.dataset import load_soccernet


def test_official_structure_and_fingerprint(tmp_path):
    for split in ("Train", "Valid", "Test"):
        folder = tmp_path / split / "action_0"
        folder.mkdir(parents=True)
        for view in range(2):
            (folder / f"clip_{view}.mp4").write_bytes(f"{split}-{view}".encode())
        (folder.parent / "annotations.json").write_text(
            json.dumps({"Actions": {"0": {"Action class": "Tackling", "Clips": [{}, {}]}}})
        )
    records, fingerprint, excluded = load_soccernet(tmp_path)
    assert len(records) == 3
    assert not excluded
    assert fingerprint == load_soccernet(tmp_path)[1]
    assert {r.incident_id for r in records} == {"Train/0", "Valid/0", "Test/0"}
    (tmp_path / "Test/action_0/clip_0.mp4").write_bytes(b"Train-0")
    with pytest.raises(ValueError, match="leakage"):
        load_soccernet(tmp_path)
