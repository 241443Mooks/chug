#!/usr/bin/env python3
"""Build and inspect a reproducible, tracked-files-only Chug submission ZIP.

Run from a clean Git checkout:
    python3 scripts/package_submission.py --output dist/chug-submission.zip

This packages *committed* content at HEAD, not working-tree changes or
untracked local state. It checks filenames and ZIP integrity, but a person
must still inspect the contents for privacy and suitability before sending.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "README.md",
    "START_HERE.md",
    "LICENSE.md",
    "chug/server.py",
    "docs/ACCEPTANCE_TESTS.md",
    "docs/DELIVERY_CHECKLIST.md",
}
BLOCKED_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
BLOCKED_SUFFIXES = {".pem", ".p12", ".pfx", ".key", ".sqlite", ".sqlite3", ".log"}
BLOCKED_FILENAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def inspect_zip(path: Path) -> int:
    """Reject missing required files, unsafe filenames and corrupt members."""
    with zipfile.ZipFile(path) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = {item.filename for item in members}
        missing = REQUIRED - names
        if missing:
            raise ValueError("Missing submission files: " + ", ".join(sorted(missing)))
        if len(names) != len(members):
            raise ValueError("Archive contains duplicate entry names")
        for item in members:
            name = item.filename
            parts = PurePosixPath(name).parts
            if not name or name.startswith("/") or ".." in parts or "\\" in name:
                raise ValueError("Unsafe archive entry: " + name)
            if (BLOCKED_PARTS.intersection(parts)
                or PurePosixPath(name).name.lower() in BLOCKED_FILENAMES
                or PurePosixPath(name).suffix.lower() in BLOCKED_SUFFIXES):
                raise ValueError("Potentially sensitive/build file in archive: " + name)
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError("Archive contains symbolic link: " + name)
        damaged = archive.testzip()
        if damaged:
            raise ValueError("Corrupt ZIP entry: " + damaged)
        return len(members)


def build(root: Path, output: Path) -> tuple[str, int]:
    root = root.resolve()
    output = output.resolve()
    # Ignore untracked local files: git archive cannot accidentally include
    # .env or local contract data that are not in version control.
    if git(root, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise ValueError("Commit or discard tracked working-tree changes before packaging")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".chug-archive-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        git(root, "archive", "--format=zip", "--output", str(temporary), "HEAD")
        count = inspect_zip(temporary)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(output)
        output.with_suffix(output.suffix + ".sha256").write_text(
            f"{digest}  {output.name}\n", encoding="utf-8"
        )
        return digest, count
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/chug-submission.zip")
    args = parser.parse_args()
    try:
        digest, count = build(ROOT, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Submission package not built: {exc}\n")
    print(f"Created {args.output.resolve()} ({count} tracked files)")
    print(f"SHA-256: {digest}")
    print("Manual privacy, content, fresh-extract and creative review still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
