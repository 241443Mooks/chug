from __future__ import annotations

import hashlib
import io
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
from unittest.mock import patch

from chug.server import App, Handler
from http.server import ThreadingHTTPServer
from chug.document import extract


ROOT = Path(__file__).resolve().parents[1]
ORDER = ROOT / "research/reference-library-v0.1/references/sales-orders/Customer Order - Desktop User Licences - Direct - v0.1.docx"


def changed_docx(source: bytes, old: bytes, new: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as updated:
        for entry in original.infolist():
            content = original.read(entry.filename)
            if entry.filename == "word/document.xml":
                content = content.replace(old, new)
            updated.writestr(entry, content)
    return output.getvalue()


class IncomingIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state = Path(self.temporary.name)
        self.app = App(ROOT, self.state)

    def tearDown(self):
        self.temporary.cleanup()

    def test_new_nda_runs_provisional_comparison_and_persists_identity_and_queue(self):
        standard = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        self.app.upload_reference(standard, "fictional-nda-standard.docx")
        incoming = changed_docx(standard, b"five years", b"seven years")

        result = self.app.intake(incoming, "new-fictional-nda.docx")
        digest = hashlib.sha256(incoming).hexdigest()
        self.assertEqual(result["incoming"]["sha256"], digest)
        self.assertEqual(result["status"], "analysed_needs_review")
        self.assertEqual(result["comparison"]["status"], "analysed")
        self.assertTrue(result["comparison"]["findings"])
        self.assertEqual(result["reference"]["sha256"], hashlib.sha256(standard).hexdigest())
        self.assertTrue(all(finding["sources"] for finding in result["comparison"]["findings"]))
        self.assertEqual((self.state / "intakes" / (digest + ".docx")).read_bytes(), incoming)
        queue_item = next(row for row in self.app.queue() if row.get("intake_sha256") == digest)
        self.assertTrue(queue_item["intake"])
        self.assertEqual(queue_item["route"], "review_required")

        restarted = App(ROOT, self.state)
        restored = restarted.intake_detail(digest)
        self.assertEqual(restored["status"], "analysed_needs_review")
        self.assertEqual(restored["reference"]["sha256"], result["reference"]["sha256"])
        self.assertEqual(restored["comparison"], result["comparison"])
        duplicate = restarted.intake(incoming, "renamed-copy.docx")
        self.assertEqual(duplicate["id"], result["id"])
        self.assertEqual(len(restarted.intakes), 1)

    def test_shared_extracted_document_seam_does_not_reparse_or_rebind(self):
        standard = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        self.app.upload_reference(standard, "fictional-nda-standard.docx")
        incoming = changed_docx(standard, b"five years", b"six years")
        extracted = extract(incoming, "unseen-contract.docx")
        with patch("chug.server.extract", side_effect=AssertionError("intake re-parsed the source")):
            result = self.app.intake_extracted(incoming, extracted)
        self.assertEqual(result["incoming"]["sha256"], extracted["sha256"])
        self.assertEqual(result["status"], "analysed_needs_review")
        self.assertEqual(result["matching"]["incoming"]["sha256"], extracted["sha256"])

    def test_customer_order_is_queued_without_bypassing_confirmation(self):
        reference = changed_docx(ORDER.read_bytes(), b"12 named desktop software users", b"13 named desktop software users")
        incoming = changed_docx(reference, b"13 named desktop software users", b"14 named desktop software users")
        self.app.upload_reference(reference, ORDER.name)

        result = self.app.intake(incoming, "fictional-customer-order.docx")
        self.assertEqual(result["family"], "customer_order")
        self.assertEqual(result["status"], "awaiting_reference")
        self.assertEqual(result["comparison"]["status"], "not_run")
        self.assertIn("explicit reviewer confirmation", result["reason"])
        self.assertEqual(result["human_decision"]["status"], "pending")
        self.assertTrue(any(row.get("intake_sha256") == result["incoming"]["sha256"] for row in self.app.queue()))

        reference_id = result["reference"]["reference_id"]
        reference_sha256 = result["reference"]["sha256"]
        with self.assertRaisesRegex(ValueError, "exact reference ID and hash"):
            self.app.confirm_intake_reference(result["incoming"]["sha256"], reference_id, "0" * 64, "Fictional reviewer", "The proposed baseline matches the transaction context.")
        confirmed = self.app.confirm_intake_reference(result["incoming"]["sha256"], reference_id, reference_sha256, "Fictional reviewer", "The proposed baseline matches the transaction context.")
        self.assertEqual(confirmed["reference_confirmation"]["status"], "confirmed")
        self.assertEqual(confirmed["comparison"]["method"], "deterministic section and text comparison")
        self.assertTrue(confirmed["comparison"]["observations"])
        first = confirmed["comparison"]["observations"][0]
        self.assertTrue(first["incoming_passages"])
        self.assertTrue(first["reference_passages"])
        event_count = len((self.state / "intake_confirmations.jsonl").read_text().splitlines())
        with self.assertRaisesRegex(ValueError, "already been confirmed"):
            self.app.confirm_intake_reference(result["incoming"]["sha256"], reference_id, reference_sha256, "Fictional reviewer", "Duplicate confirmation")
        self.assertEqual(len((self.state / "intake_confirmations.jsonl").read_text().splitlines()), event_count)

        decision = self.app.record_intake_decision(result["incoming"]["sha256"], "Fictional reviewer", "request_amendment", "Please restore the contracted seat quantity.", finding_ids=[first["id"]])
        self.assertEqual(decision["decision"], "request_amendment")
        restored = App(ROOT, self.state).intake_detail(result["incoming"]["sha256"])
        self.assertEqual(restored["human_decision"]["status"], "recorded")
        self.assertEqual(restored["human_decision"]["last_decision"]["id"], decision["id"])

    def test_ambiguous_no_match_and_corrupt_uploads_remain_visible(self):
        nda = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        no_match = self.app.intake(nda, "unmatched-fictional-nda.docx")
        self.assertEqual(no_match["status"], "awaiting_reference")
        self.assertEqual(no_match["comparison"]["status"], "not_run")

        corrupt = self.app.intake(b"not a DOCX package", "corrupted.docx")
        self.assertEqual(corrupt["status"], "blocked_extraction")
        self.assertEqual(corrupt["route"], "blocked_extraction")
        self.assertEqual(corrupt["comparison"]["status"], "not_run")
        self.assertEqual(len(self.app.intakes), 2)
        self.assertEqual(sum(row.get("intake", False) for row in self.app.queue()), 2)

    def test_tied_active_references_queue_for_clarification_without_comparison(self):
        standard = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        second_standard = changed_docx(standard, b"five years", b"six years")
        incoming = changed_docx(standard, b"five years", b"seven years")
        self.app.upload_reference(standard, "fictional-nda-standard-one.docx")
        self.app.upload_reference(second_standard, "fictional-nda-standard-two.docx")

        result = self.app.intake(incoming, "tied-fictional-nda.docx")
        self.assertEqual(result["matching"]["proposal"]["status"], "ambiguous_match")
        self.assertEqual(result["status"], "awaiting_reference")
        self.assertEqual(result["comparison"]["status"], "not_run")
        self.assertTrue(any(row.get("intake_sha256") == result["incoming"]["sha256"] for row in self.app.queue()))

    def test_intake_record_tampering_blocks_restart(self):
        data = b"not a DOCX package"
        result = self.app.intake(data, "corrupted.docx")
        meta = self.state / "intakes" / (result["incoming"]["sha256"] + ".json")
        record = json.loads(meta.read_text())
        record["status"] = "analysed_needs_review"
        meta.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            App(ROOT, self.state)

    def test_upload_queue_detail_and_original_are_available_through_local_api(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Handler.app = self.app
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            boundary = "issue-eight-intake"
            source = b"not a DOCX package"
            multipart = (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"corrupt.docx\"\r\n"
                "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
            ).encode() + source + f"\r\n--{boundary}--\r\n".encode()
            request = Request(f"http://127.0.0.1:{server.server_port}/api/intakes", data=multipart, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            created = json.loads(urlopen(request).read())
            digest = created["incoming"]["sha256"]
            queue = json.loads(urlopen(f"http://127.0.0.1:{server.server_port}/api/queue").read())["items"]
            self.assertTrue(any(row.get("intake_sha256") == digest for row in queue))
            detail = json.loads(urlopen(f"http://127.0.0.1:{server.server_port}/api/intakes/{digest}").read())
            self.assertEqual(detail["status"], "blocked_extraction")
            original = urlopen(f"http://127.0.0.1:{server.server_port}/api/intakes/{digest}/original").read()
            self.assertEqual(original, source)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    unittest.main()
