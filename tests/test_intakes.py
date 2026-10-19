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

    def test_registered_specimens_are_found_and_compared_without_per_upload_selection(self):
        specimens = [
            ("references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx", "Incoming - Desktop Reseller Seat Increase.docx", "customer_order", "complete"),
            ("references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx", "Incoming - Evaluation NDA with Longer Retention.docx", "nda", "analysed"),
        ]
        base = ROOT / "research/reference-library-v0.1"
        for reference_name, incoming_name, family, expected_status in specimens:
            source = base / reference_name
            incoming = base / "incoming-tests" / incoming_name
            registered = self.app.upload_reference(source.read_bytes(), source.name)["library_item"]
            self.assertEqual(registered["status"], "active")
            self.assertEqual(registered["family"], family)
            self.assertTrue(any(row["sha256"] == registered["sha256"] and row["status"] == "research_candidate" for row in self.app.reference_library_list()["references"]))
            detail = self.app.intake(incoming.read_bytes(), incoming.name)
            self.assertEqual(detail["comparison"]["status"], expected_status)
            self.assertEqual(detail["reference"]["sha256"], registered["sha256"])
            self.assertIn(detail["matching"]["proposal"]["status"], {"proposed", "proposed_with_gaps"})
            self.assertTrue(detail["comparison"]["provisional"])
            self.assertNotIn("reference_confirmation", detail)
            self.assertEqual(detail["human_decision"]["status"], "pending")
            restored = App(ROOT, self.state).intake_detail(detail["incoming"]["sha256"])
            self.assertEqual(restored["comparison"], detail["comparison"])
            duplicate = self.app.intake(incoming.read_bytes(), "copy.docx")
            self.assertEqual(duplicate["id"], detail["id"])
        self.assertEqual(len(self.app.intakes), 2)


    def test_starter_reproduces_all_five_submission_scenarios(self):
        from scripts.seed_synthetic_starter import seed

        first = seed(self.state)
        self.assertEqual(len(first), 5)
        self.assertEqual([row["example"] for row in first], [
            "exact copy", "changed wording", "exact copy", "changed wording", "ambiguous purchase",
        ])
        for row in first[:4]:
            self.assertEqual(row["selected_reference_id"], row["expected_reference_id"])
            self.assertIn(row["comparison_status"], {"analysed", "complete"})
            self.assertEqual(row["human_decision"], "pending")
        abstained = first[-1]
        self.assertIsNone(abstained["selected_reference_id"])
        self.assertEqual(abstained["comparison_status"], "not_run")
        self.assertEqual(abstained["human_decision"], "pending")
        self.assertTrue(abstained["reason"])
        repeated = seed(self.state)
        self.assertEqual(
            [(row["incoming_sha256"], row["selected_reference_id"], row["comparison_status"]) for row in repeated],
            [(row["incoming_sha256"], row["selected_reference_id"], row["comparison_status"]) for row in first],
        )
        self.assertEqual(len(App(ROOT, self.state).intakes), 5)


    def test_explicit_wrong_family_and_unverified_reference_are_blocked(self):
        standard = (ROOT / "research/reference-library-v0.1/references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx")
        incoming = (ROOT / "research/reference-library-v0.1/incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx")
        registered = self.app.upload_reference(standard.read_bytes(), standard.name)["library_item"]
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.app.intake(incoming.read_bytes(), incoming.name, registered["reference_id"], "Fictional reviewer", "Wrong family")
        self.assertEqual(len(self.app.intakes), 0)
        with self.assertRaisesRegex(ValueError, "Active reference"):
            self.app.intake(incoming.read_bytes(), incoming.name, "ORDER-RESELLER", "Fictional reviewer", "Research only")

    def test_exact_reference_copies_have_no_reported_differences_but_still_need_review(self):
        base = ROOT / "research/reference-library-v0.1/references"
        for relative in ("nda/Mutual NDA - Product Evaluation - UK - v0.1.docx", "sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx"):
            source = base / relative
            data = source.read_bytes()
            registered = self.app.upload_reference(data, source.name)["library_item"]
            result = self.app.intake(data, "Incoming " + source.name)
            self.assertEqual(result["comparison"].get("findings", result["comparison"].get("observations")), [])
            self.assertEqual(result["human_decision"]["status"], "pending")
            self.assertEqual(result["reference"]["sha256"], registered["sha256"])
            self.assertNotIn("reference_confirmation", result)

    def test_http_explicit_reference_upload_runs_comparison(self):
        source = ROOT / "research/reference-library-v0.1/references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx"
        incoming = ROOT / "research/reference-library-v0.1/incoming-tests/Incoming - Desktop Reseller Seat Increase.docx"
        reference_id = self.app.upload_reference(source.read_bytes(), source.name)["library_item"]["reference_id"]
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Handler.app = self.app
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            boundary = "explicit-reference"
            fields = [("reference_id", reference_id), ("reviewer", "Fictional reviewer"), ("rationale", "Reseller desktop scope applies.")]
            body = b"".join((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode() for name, value in fields)
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="incoming.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + incoming.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
            request = Request(f"http://127.0.0.1:{server.server_port}/api/intakes", data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            result = json.loads(urlopen(request).read())
            self.assertEqual(result["comparison"]["status"], "complete")
            self.assertEqual(result["reference_confirmation"]["reference_id"], reference_id)
            self.assertEqual(result["human_decision"]["status"], "pending")
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_batch_runs_each_source_automatically_and_is_idempotent(self):
        base = ROOT / "research/reference-library-v0.1"
        nda_ref = base / "references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx"
        order_ref = base / "references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx"
        for source in (nda_ref, order_ref):
            self.app.upload_reference(source.read_bytes(), source.name)
        files = [(path.name, path.read_bytes()) for path in (
            base / "incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx",
            base / "incoming-tests/Incoming - Desktop Reseller Seat Increase.docx",
            base / "incoming-tests/Incoming - Ambiguous Reseller Cloud Scan Purchase.docx",
        )]
        files.append(("not-a-contract.txt", b"unsupported"))
        batch = self.app.intake_batch(files)
        self.assertEqual(batch["counts"], {"analysed": 2, "awaiting_reference": 1, "blocked_extraction": 0, "duplicate": 0, "failed": 1})
        self.assertEqual([row["comparison_status"] for row in batch["items"][:3]], ["analysed", "complete", "not_run"])
        self.assertEqual(len(self.app.intakes), 3)
        repeated = App(ROOT, self.state).intake_batch(files)
        self.assertEqual(repeated["counts"]["duplicate"], 3)
        self.assertEqual(repeated["counts"]["failed"], 1)
        self.assertEqual([row.get("id") for row in repeated["items"][:3]], [row["id"] for row in batch["items"][:3]])
        with self.assertRaisesRegex(ValueError, "1 to 20"):
            self.app.intake_batch(files * 6)

    def test_http_batch_accepts_multiple_files_and_reports_per_file_state(self):
        base = ROOT / "research/reference-library-v0.1"
        source = base / "references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx"
        changed = base / "incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx"
        self.app.upload_reference(source.read_bytes(), source.name)
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Handler.app = self.app
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            boundary = "batch-intake"
            body = b""
            for filename, data in [("exact.docx", source.read_bytes()), (changed.name, changed.read_bytes()), ("unsupported.txt", b"text")]:
                body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + b"\r\n"
            body += f"--{boundary}--\r\n".encode()
            request = Request(f"http://127.0.0.1:{server.server_port}/api/intakes/batch", data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            batch = json.loads(urlopen(request).read())
            self.assertEqual(batch["counts"]["analysed"], 2)
            self.assertEqual(batch["counts"]["failed"], 1)
            self.assertEqual(batch["items"][0]["comparison_status"], "analysed")
            self.assertEqual(batch["items"][2]["outcome"], "failed")
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_directory_feed_pass_uses_batch_pipeline_and_deduplicates(self):
        from scripts.ingest_directory import ingest

        base = ROOT / "research/reference-library-v0.1"
        source = base / "references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx"
        changed = base / "incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx"
        self.app.upload_reference(source.read_bytes(), source.name)
        drop = self.state / "drop"
        drop.mkdir()
        (drop / "exact.docx").write_bytes(source.read_bytes())
        (drop / "changed.docx").write_bytes(changed.read_bytes())
        first = ingest(self.state, drop)
        self.assertEqual(first["counts"]["analysed"], 2)
        self.assertEqual(ingest(self.state, drop)["counts"]["duplicate"], 2)

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

    def test_customer_order_is_compared_automatically_but_remains_unconfirmed(self):
        reference = changed_docx(ORDER.read_bytes(), b"12 named desktop software users", b"13 named desktop software users")
        incoming = changed_docx(reference, b"13 named desktop software users", b"14 named desktop software users")
        self.app.upload_reference(reference, ORDER.name)

        result = self.app.intake(incoming, "fictional-customer-order.docx")
        self.assertEqual(result["family"], "customer_order")
        self.assertEqual(result["status"], "analysed_needs_review")
        self.assertEqual(result["comparison"]["status"], "complete")
        self.assertTrue(result["comparison"]["provisional"])
        self.assertNotIn("reference_confirmation", result)
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

    def test_approval_requires_and_records_independent_original_review(self):
        source = b"not a DOCX package"
        intake = self.app.intake(source, "blocked.docx")
        digest = intake["incoming"]["sha256"]
        with self.assertRaisesRegex(ValueError, "independently reviewed the exact incoming original"):
            self.app.record_intake_decision(digest, "Fictional reviewer", "approve", "Reviewed", independent_original_reviewed=False)
        decision = self.app.record_intake_decision(digest, "Fictional reviewer", "approve", "Reviewed the source despite blocked extraction", independent_original_reviewed=True)
        self.assertTrue(decision["independent_original_reviewed"])
        self.assertEqual(self.app.intake_detail(digest)["human_decision"]["status"], "recorded")

    def test_saved_comparison_reports_reference_source_unavailable_after_removal(self):
        standard = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        self.app.upload_reference(standard, "fictional-nda-standard.docx")
        incoming = changed_docx(standard, b"five years", b"seven years")
        result = self.app.intake(incoming, "new-fictional-nda.docx")
        reference_path = self.app.references[result["reference"]["sha256"]]["path"]
        reference_path.unlink()
        restored = self.app.intake_detail(result["incoming"]["sha256"])
        self.assertEqual(restored["comparison"]["status"], "analysed")
        self.assertEqual(restored["source_integrity"]["reference"], "unavailable")

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
