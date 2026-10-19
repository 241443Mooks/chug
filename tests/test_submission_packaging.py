"""Exercise reproducible ZIP creation without packaging local untracked data."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_submission import REQUIRED, build


class SubmissionZipTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for name in REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fictional source only\n", encoding="utf-8")
        self.run_git("add", ".")
        self.commit("Initial fictional submission")

    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def commit(self, message):
        self.run_git("-c", "user.name=Chug Test", "-c", "user.email=test@example.invalid", "commit", "-qm", message)

    def test_only_committed_files_are_packaged_and_checksum_recorded(self):
        (self.root / ".env").write_text("DO_NOT_INCLUDE=1", encoding="utf-8")
        (self.root / "local-private-contract.docx").write_bytes(b"NOT FOR SUBMISSION")
        destination = Path(self.temporary.name) / "output/chug-submission.zip"
        digest, count = build(self.root, destination)
        self.assertEqual(count, len(REQUIRED))
        self.assertEqual(len(digest), 64)
        self.assertTrue(destination.with_suffix(".zip.sha256").exists())
        with zipfile.ZipFile(destination) as archive:
            files = {item.filename for item in archive.infolist() if not item.is_dir()}
            self.assertEqual(files, REQUIRED)
            self.assertNotIn(".env", files)
            self.assertNotIn("local-private-contract.docx", archive.namelist())
            self.assertIsNone(archive.testzip())

    def test_dirty_tracked_source_is_rejected(self):
        (self.root / "README.md").write_text("uncommitted change", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Commit or discard"):
            build(self.root, Path(self.temporary.name) / "dirty.zip")

    def test_committed_secret_filename_is_rejected(self):
        (self.root / ".env").write_text("FAKE_TOKEN=example", encoding="utf-8")
        self.run_git("add", "-f", ".env")
        self.commit("Accidentally tracked environment file")
        destination = Path(self.temporary.name) / "unsafe.zip"
        with self.assertRaisesRegex(ValueError, "Potentially sensitive"):
            build(self.root, destination)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
