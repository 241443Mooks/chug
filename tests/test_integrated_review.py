"""Exercise automatic selection and human review together, with real originals."""
import tempfile
import unittest
from pathlib import Path

from chug.server import App

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "research/reference-library-v0.1"


class IntegratedReviewTests(unittest.TestCase):
    def test_automatic_findings_keep_evidence_and_human_history_across_confirmation_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            app = App(ROOT, Path(temp))
            for ref, incoming in (
                ("nda/Mutual NDA - Product Evaluation - UK - v0.1.docx", "Incoming - Evaluation NDA with Longer Retention.docx"),
                ("sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx", "Incoming - Desktop Reseller Seat Increase.docx"),
            ):
                source = LIBRARY / "references" / ref
                registered = app.upload_reference(source.read_bytes(), source.name)["library_item"]
                path = LIBRARY / "incoming-tests" / incoming
                detail = app.intake(path.read_bytes(), "new-contract.docx")
                digest, case_id = detail["incoming"]["sha256"], detail["id"]
                self.assertNotIn("reference_confirmation", detail)
                self.assertEqual(detail["human_decision"]["status"], "pending")
                rows = (detail["analysis"] or {}).get("findings") or detail["comparison"].get("observations")
                finding = rows[-1]
                assessment = app.assess_finding(case_id, finding["id"], "problem", "Test reviewer", "Check the changed provision.")
                self.assertEqual(assessment["reference_id"], registered["reference_id"])
                self.assertEqual(assessment["reference_sha256"], registered["sha256"])
                self.assertEqual(assessment["source_sha256"], digest)
                self.assertEqual(assessment["evidence"]["reference"], finding.get("reference_passages") or finding.get("reference"))
                self.assertEqual(app.intake_detail(digest)["human_decision"]["status"], "pending")
                with self.assertRaises(ValueError):
                    app.record_contract_action(case_id, "accept_contract", "Test reviewer", "Accept", True)
                flag = app.record_contract_action(case_id, "flag_for_review", "Test reviewer", "Seek further input.")
                self.assertEqual(app.intake_detail(digest)["review_state"], "flagged")
                confirmed = app.confirm_intake_reference(digest, registered["reference_id"], registered["sha256"], "Test reviewer", "Checked scope and parties against the exact source.")
                self.assertEqual(confirmed["latest_finding_assessments"][finding["id"]], assessment)
                revised = app.assess_finding(case_id, finding["id"], "acceptable", "Test reviewer", "Resolved after independent review.")
                self.assertEqual(revised["supersedes"], assessment["id"])
                accepted = app.record_contract_action(case_id, "accept_contract", "Test reviewer", "Independently inspected the original and all remaining findings for this synthetic test.", True, True)
                restored = App(ROOT, Path(temp))
                duplicate = restored.intake(path.read_bytes(), "renamed.docx")
                self.assertEqual(duplicate["id"], case_id)
                self.assertEqual(duplicate["reference"]["sha256"], registered["sha256"])
                self.assertEqual(duplicate["human_decision"]["outcome"], "approve")
                self.assertEqual([e["id"] for e in duplicate["contract_actions"]], [flag["id"], accepted["id"]])
                self.assertEqual(len(duplicate["finding_assessments"]), 2)
                self.assertEqual(duplicate["latest_finding_assessments"][finding["id"]], revised)
                self.assertEqual(duplicate["reference_document"]["sha256"], registered["sha256"])

    def test_missing_order_section_can_be_assessed_against_reference_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            app = App(ROOT, Path(temp))
            path = LIBRARY / "references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx"
            app.upload_reference(path.read_bytes(), path.name)
            # Remove an entire section, retaining the genuine extracted remaining content.
            import io
            import zipfile
            import xml.etree.ElementTree as ET
            out = io.BytesIO()
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            with zipfile.ZipFile(path) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    data = src.read(item.filename)
                    if item.filename == "word/document.xml":
                        xml = ET.fromstring(data)
                        body = xml.find("w:body", ns)
                        paragraphs = list(body)
                        for index, paragraph in enumerate(paragraphs):
                            text = "".join(paragraph.itertext())
                            if text.startswith("2. "):
                                body.remove(paragraph)
                                body.remove(paragraphs[index + 1])
                        data = ET.tostring(xml)
                    dst.writestr(item, data)
            detail = app.intake(out.getvalue(), "missing-section.docx")
            missing = next(f for f in detail["comparison"]["observations"] if f["difference_type"] == "missing_section")
            event = app.assess_finding(detail["id"], missing["id"], "needs_further_review", "Test reviewer", "Check whether the protection occurs elsewhere.")
            self.assertEqual(event["evidence"]["sources"], [])
            self.assertTrue(event["evidence"]["reference"])

    def test_unverified_reference_cannot_acquire_an_assessment(self):
        with tempfile.TemporaryDirectory() as temp:
            app = App(ROOT, Path(temp))
            path = LIBRARY / "references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx"
            ref = app.upload_reference(path.read_bytes(), path.name)["library_item"]
            incoming = LIBRARY / "incoming-tests/Incoming - Desktop Reseller Seat Increase.docx"
            detail = app.intake(incoming.read_bytes(), incoming.name)
            app.reference_library[ref["reference_id"]]["path"].write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "not verified"):
                app.assess_finding(detail["id"], detail["comparison"]["observations"][0]["id"], "acceptable", "Test reviewer", "")
            self.assertIsNone(app.intake_detail(detail["incoming"]["sha256"])["reference_document"])


if __name__ == "__main__":
    unittest.main()
