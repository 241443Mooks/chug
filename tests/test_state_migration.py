"""Check the default data-directory rename without losing existing local review history."""
import tempfile
import unittest
from pathlib import Path

from chug.server import default_state_dir


class StateMigrationTests(unittest.TestCase):
    def test_old_state_is_copied_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / ".chugchug-data"
            old.mkdir()
            (old / "decisions.jsonl").write_text('{"event":"example"}\n', encoding="utf-8")
            new = default_state_dir(root)
            self.assertEqual(new, root / ".chug-data")
            self.assertEqual((new / "decisions.jsonl").read_bytes(), (old / "decisions.jsonl").read_bytes())
            self.assertTrue(old.is_dir(), "Original directory must be kept as a backup")

    def test_existing_new_state_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old, new = root / ".chugchug-data", root / ".chug-data"
            old.mkdir()
            new.mkdir()
            (old / "decisions.jsonl").write_text("old", encoding="utf-8")
            (new / "decisions.jsonl").write_text("current", encoding="utf-8")
            self.assertEqual(default_state_dir(root), new)
            self.assertEqual((new / "decisions.jsonl").read_text(), "current")

    def test_new_install_uses_chug_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(default_state_dir(root), root / ".chug-data")
            self.assertFalse((root / ".chug-data").exists())


if __name__ == "__main__":
    unittest.main()
