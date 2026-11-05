"""Extract official downloaded split archives into ignored local storage."""

import argparse
import os
import shutil
from pathlib import Path

import pyzipper
from dotenv import load_dotenv


def extract(archive, destination, password):
    destination = destination.resolve()
    with pyzipper.AESZipFile(archive) as source:
        source.setpassword(password.encode())
        entries = source.infolist()
        for entry in entries:
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive contains an unsafe path")
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Archive symlinks are not supported")
        required = sum(e.file_size for e in entries)
        destination.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(destination).free < required + 2**30:
            raise ValueError("Insufficient disk for extraction plus 1 GiB reserve")
        # Verify CRC/authentication tags while decrypting each member.
        source.extractall(destination)
    print(f"Extracted {archive.name}: {len(entries)} members", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=Path("data/soccernet/mvfouls"))
    parser.add_argument("--output", type=Path, default=Path("data/soccernet/mvfouls"))
    args = parser.parse_args()
    load_dotenv()
    password = os.getenv("SOCCERNET_PASSWORD")
    if not password:
        parser.error("Set SOCCERNET_PASSWORD in ignored .env")
    for split, folder in (("train", "Train"), ("valid", "Valid"), ("test", "Test")):
        extract(args.archives / f"{split}.zip", args.output / folder, password)


if __name__ == "__main__":
    main()
