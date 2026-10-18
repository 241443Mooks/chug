"""The active NDA rules are called through the contract-family boundary."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chug.nda_pack import NDAPack
from chug.server import App

ROOT = Path(__file__).resolve().parents[1]


class ObservedNDAPack(NDAPack):
    def __init__(self):
        self.validations = 0
        self.analyses = 0

    def validate_reference(self, document, bundled_reference):
        self.validations += 1
        return super().validate_reference(document, bundled_reference)

    def analyse(self, reference, document, historical, decisions, published, bundled_reference):
        self.analyses += 1
        return super().analyse(reference, document, historical, decisions, published, bundled_reference)


class NDAPackBoundaryTests(unittest.TestCase):
    def test_reference_policy_and_analysis_run_through_active_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = ObservedNDAPack()
            app = App(ROOT, Path(directory), pack=pack)
            self.assertEqual(app.pack.id, "mutual_nda")
            self.assertEqual(app.detail("T03")["analysis"]["route"], "escalate")
            self.assertEqual(pack.analyses, 1)
            unsupported = (ROOT / "dataset/incoming/T04-missing-no-licence.docx").read_bytes()
            with self.assertRaisesRegex(ValueError, "missing clause headings"):
                app.upload_reference(unsupported, "fictional-unsupported.docx")
            self.assertEqual(pack.validations, 1)
            self.assertEqual(app.detail("T01")["analysis"]["route"], "routine_candidate")


if __name__ == "__main__":
    unittest.main()
