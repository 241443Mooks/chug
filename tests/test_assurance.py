from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from chug.document import extract_file
from chug.engine import analyse, load_library, validate_decisions
from chug.server import App
from tests.adversarial_audit import audit

ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL = ROOT / "dataset/adversarial"


class AssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference, cls.historical, _, cls.decisions = load_library(ROOT)

    def report(self, stem):
        document = extract_file(next(ADVERSARIAL.glob(stem + "-*.docx")))
        return document, analyse(self.reference, document, self.historical, self.decisions)

    def test_all_critical_challenges_surface_and_anchors_resolve(self):
        result = audit()
        recall = result["metrics"]["critical_exception_recall"]
        self.assertEqual(recall["surfaced"], recall["total"])
        self.assertEqual(recall["total"], 11)
        self.assertEqual(result["metrics"]["false_routine_recommendations"]["count"], 0)
        self.assertTrue(all(row["valid_evidence"] for row in result["cases"]))

    def test_nonbody_differences_are_compared_and_scanned(self):
        for case, part, category in (("A01", "word/footer1.xml", "broad_rights"), ("A02", "word/header1.xml", "override")):
            with self.subTest(case=case):
                document, report = self.report(case)
                self.assertEqual(report["route"], "escalate")
                self.assertTrue(any(f["category"] == "changed_document_part" for f in report["findings"]))
                self.assertTrue(any(f["category"] == category and f["sources"][0]["part"] == part for f in report["findings"]))
                self.assertEqual(report["assurance"]["safeguards"]["passages_examined"], len(document["units"]))

    def test_ambiguous_or_hidden_content_blocks_shortcut(self):
        for case in ("A03", "A04", "A14", "A15"):
            with self.subTest(case=case):
                _, report = self.report(case)
                self.assertEqual(report["route"], "blocked_extraction")
                self.assertEqual(report["assurance"]["comparison"]["status"], "not run")
                self.assertTrue(report["assurance"]["limitations"])
        _, report = self.report("A05")
        self.assertEqual(report["assurance"]["comparison"]["status"], "limited")
        self.assertTrue(any(f["category"] == "structural_ambiguity" for f in report["findings"]))
        _, disabled_formatting = self.report("A16")
        self.assertEqual(disabled_formatting["route"], "routine_candidate")

    def test_negated_controls_do_not_create_false_critical_findings(self):
        for case in ("A09", "A10"):
            with self.subTest(case=case):
                _, report = self.report(case)
                self.assertEqual(report["route"], "review_required")
                self.assertFalse(any(f["route"] == "escalate" for f in report["findings"]))

    def test_assurance_and_human_status_come_from_events(self):
        with tempfile.TemporaryDirectory() as temp:
            app = App(ROOT, Path(temp))
            before = app.detail("T03")
            self.assertEqual(before["analysis"]["assurance"]["human_review"]["status"], "not recorded")
            source = before["analysis"]["assurance"]["source_integrity"]
            self.assertEqual(source["sha256"], before["document"]["sha256"])
            self.assertEqual(source["bytes"], before["document"]["size"])
            app.ledger.append(source["sha256"], before["document"]["filename"], "Assurance tester", "escalate", "Needs counsel review.", [])
            after = App(ROOT, Path(temp)).detail("T03")
            self.assertEqual(after["analysis"]["assurance"]["human_review"], {"status": "recorded", "last_decision": "escalate", "events": 1})

    def test_interrupted_or_tampered_upload_is_not_silently_lost(self):
        sample = (ROOT / "dataset/incoming/T01-template-match.docx").read_bytes()
        digest = hashlib.sha256(sample).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            app = App(ROOT, state)
            app.upload(sample, "synthetic.docx")
            self.assertIn("U-" + digest[:10], App(ROOT, state).contracts)
            metadata = state / "uploads" / (digest + ".json")
            metadata.unlink()
            with self.assertRaisesRegex(ValueError, "Upload recovery required"):
                App(ROOT, state)
            # A repeated upload repairs the interrupted original/metadata pair.
            app.upload(sample, "synthetic.docx")
            self.assertIn("U-" + digest[:10], App(ROOT, state).contracts)
            metadata.write_text(json.dumps({"id": "wrong", "sha256": digest, "filename": "synthetic.docx"}))
            with self.assertRaisesRegex(ValueError, "source identity mismatch"):
                App(ROOT, state)
            (state / "uploads" / (digest + ".docx")).write_bytes(b"tampered")
            compromised = app.analysis("U-" + digest[:10])
            self.assertEqual(compromised["route"], "blocked_extraction")
            self.assertEqual(compromised["assurance"]["source_integrity"]["status"], "mismatch")

    def test_precedent_register_rejects_duplicate_or_incomplete_records(self):
        row = {"document_id": "H01", "decision": "accepted", "rationale": "Reviewed in its specific context.", "reviewer": "Fictional reviewer", "decision_date": "2026-08-10", "reuse_authority": "illustrative only"}
        self.assertEqual(validate_decisions([row], {"H01"})["H01"], row)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_decisions([row, row], {"H01"})
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validate_decisions([{**row, "rationale": ""}], {"H01"})
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            validate_decisions([{**row, "decision": "approved_as_policy"}], {"H01"})


if __name__ == "__main__":
    unittest.main()
