"""Reference choice is an immutable analysis binding, not a mutable global label."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from chug.server import App

ROOT = Path(__file__).resolve().parents[1]


class ReferenceSelectionTests(unittest.TestCase):
    def test_chosen_reference_survives_restart_without_relabelling_earlier_work(self):
        custom = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        incoming = (ROOT / "dataset/incoming/T06-paraphrase-equivalent.docx").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            app = App(ROOT, state)
            bundled_sha = app.reference["sha256"]
            original_route = app.detail("T03")["analysis"]["route"]
            chosen = app.upload_reference(custom, "fictional-chosen-reference.docx")
            chosen_sha = chosen["current"]["sha256"]
            self.assertEqual(chosen_sha, hashlib.sha256(custom).hexdigest())
            self.assertEqual(chosen["current"]["source_integrity"], "verified")
            self.assertEqual(app.detail("T03")["reference"]["sha256"], bundled_sha)
            self.assertEqual(app.detail("T03")["analysis"]["route"], original_route)

            custom_id = app.upload(incoming, "later-fictional.docx")
            self.assertEqual(app.upload(incoming, "same-bytes.docx"), custom_id)
            custom_detail = app.detail(custom_id)
            self.assertEqual(custom_detail["reference"]["sha256"], chosen_sha)
            self.assertEqual(custom_detail["analysis"]["reference_sha256"], chosen_sha)
            self.assertEqual(custom_detail["analysis"]["route"], "review_required")
            self.assertEqual(len(custom_detail["analysis"]["findings"]), 2)
            matching_id = app.upload(custom, "same-as-reference.docx")
            matching = app.detail(matching_id)
            self.assertEqual(matching["analysis"]["findings"], [])
            self.assertEqual(matching["analysis"]["route"], "review_required")
            self.assertIn("not been approved", " ".join(matching["analysis"]["assurance"]["limitations"]))
            event = app.ledger.append(custom_detail["document"]["sha256"], custom_detail["document"]["filename"], "Fictional reviewer", "request_amendment", "Review the two changed clauses.", [], reference_sha256=chosen_sha)
            self.assertEqual(event["reference_sha256"], chosen_sha)

            app.select_reference(bundled_sha)
            bundled_id = app.upload(incoming, "later-fictional.docx")
            self.assertNotEqual(bundled_id, custom_id)
            self.assertEqual(app.detail(bundled_id)["reference"]["sha256"], bundled_sha)
            self.assertEqual(len(app.detail(bundled_id)["analysis"]["findings"]), 1)
            self.assertFalse(app.detail(bundled_id)["history"])
            self.assertEqual(len(app.detail(custom_id)["history"]), 1)

            restarted = App(ROOT, state)
            self.assertEqual(restarted.active_reference_sha256, bundled_sha)
            self.assertEqual(restarted.detail(custom_id)["reference"]["sha256"], chosen_sha)
            self.assertEqual(restarted.detail(custom_id)["history"][0]["id"], event["id"])

    def test_unsupported_reference_and_tampering_cannot_enable_shortcut(self):
        no_licence = (ROOT / "dataset/incoming/T04-missing-no-licence.docx").read_bytes()
        valid = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            app = App(ROOT, state)
            with self.assertRaisesRegex(ValueError, "missing clause headings"):
                app.upload_reference(no_licence, "unsupported.docx")
            chosen_sha = app.upload_reference(valid, "valid.docx")["current"]["sha256"]
            uploaded = app.upload((ROOT / "dataset/incoming/T06-paraphrase-equivalent.docx").read_bytes(), "later.docx")
            original = state / "references" / (chosen_sha + ".docx")
            original.write_bytes(b"tampered")
            self.assertEqual(app.detail(uploaded)["analysis"]["route"], "blocked_extraction")
            with self.assertRaisesRegex(ValueError, "changed"):
                app.select_reference(chosen_sha)
            with self.assertRaisesRegex(ValueError, "Reference recovery required"):
                App(ROOT, state)

    def test_interrupted_reference_write_stops_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "references").mkdir()
            (state / "references" / "broken.uploading").write_bytes(b"partial")
            with self.assertRaisesRegex(ValueError, "interrupted write"):
                App(ROOT, state)


if __name__ == "__main__":
    unittest.main()
