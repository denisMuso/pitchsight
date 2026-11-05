import pytest

pyzipper = pytest.importorskip("pyzipper")

from scripts.prepare_soccernet import extract  # noqa: E402


def test_encrypted_archive_and_path_validation(tmp_path):
    archive = tmp_path / "fixture.zip"
    with pyzipper.AESZipFile(archive, "w", encryption=pyzipper.WZ_AES) as output:
        output.setpassword(b"fixture-only")
        output.writestr("action_0/clip_0.mp4", b"engineering fixture")
    extract(archive, tmp_path / "extracted", "fixture-only")
    assert (tmp_path / "extracted/action_0/clip_0.mp4").read_bytes() == b"engineering fixture"
    with pytest.raises(RuntimeError):
        extract(archive, tmp_path / "wrong", "incorrect")
    with pyzipper.AESZipFile(archive, "w") as output:
        output.writestr("../outside.txt", "unsafe")
    with pytest.raises(ValueError, match="unsafe"):
        extract(archive, tmp_path / "safe", "fixture-only")
    assert not (tmp_path / "outside.txt").exists()
