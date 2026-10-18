from __future__ import annotations

import hashlib
import json
import io
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from chug.server import App, Handler


ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_ORDER = ROOT / "research/reference-library-v0.1/references/sales-orders/Customer Order - Desktop User Licences - Direct - v0.1.docx"


def new_customer_order_bytes(users=13):
    """Create a distinct synthetic upload from the research specimen without touching it."""
    source = CUSTOMER_ORDER.read_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as updated:
        for entry in original.infolist():
            content = original.read(entry.filename)
            if entry.filename == "word/document.xml":
                content = content.replace(b"12 named desktop software users", f"{users} named desktop software users".encode())
            updated.writestr(entry, content)
    return output.getvalue()


class ReferenceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.app = App(ROOT, self.state)

    def tearDown(self):
        self.temp.cleanup()

    def test_customer_order_reference_persists_active_without_changing_nda(self):
        data = new_customer_order_bytes()
        baseline = self.app.active_reference_sha256
        item = self.app.upload_reference(data, CUSTOMER_ORDER.name)["library_item"]
        digest = hashlib.sha256(data).hexdigest()

        self.assertEqual(item["family"], "customer_order")
        self.assertEqual(item["sha256"], digest)
        self.assertEqual(item["status"], "active")
        self.assertNotIn("approval_status", item)
        self.assertEqual(item["provenance"], "locally_uploaded_synthetic_reference")
        self.assertEqual(item["extraction"]["status"], "complete")
        self.assertEqual(item["applicability"]["jurisdiction"]["state"], "unknown")
        self.assertEqual(self.app.active_reference_sha256, baseline)
        stored = self.state / "references" / (digest + ".docx")
        self.assertEqual(stored.read_bytes(), data)
        saved_metadata = json.loads((self.state / "references" / (digest + ".json")).read_text())
        self.assertEqual(saved_metadata["sha256"], digest)
        self.assertEqual(saved_metadata["family"], "customer_order")

        restarted = App(ROOT, self.state)
        restored = restarted.reference_library_detail(item["reference_id"])
        self.assertEqual(restored["sha256"], digest)
        self.assertEqual(restored["source_integrity"], "verified")
        self.assertEqual(restored["document"]["units"], item_document_units(data, CUSTOMER_ORDER.name))
        self.assertEqual(restarted.active_reference_sha256, baseline)

        duplicate = restarted.upload_reference(data, "renamed-customer-order.docx")["library_item"]
        self.assertEqual(duplicate["reference_id"], item["reference_id"])
        self.assertEqual(duplicate["original_filename"], item["original_filename"])
        self.assertEqual(duplicate["version"], item["version"])
        self.assertEqual(duplicate["status"], "active")
        self.assertEqual(len(list((self.state / "references").glob("*.docx"))), 1)

    def test_supported_nda_upload_retains_existing_selection_behavior_and_family_isolation(self):
        customer_data = new_customer_order_bytes()
        self.app.upload_reference(customer_data, CUSTOMER_ORDER.name)
        bundled_sha = self.app.bundled_reference_sha256
        nda_data = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        result = self.app.upload_reference(nda_data, "fictional-mutual-nda.docx")

        self.assertEqual(result["library_item"]["family"], "nda")
        self.assertEqual(result["library_item"]["status"], "active")
        self.assertEqual(result["current"]["sha256"], hashlib.sha256(nda_data).hexdigest())
        self.assertNotEqual(self.app.active_reference_sha256, bundled_sha)
        self.assertEqual(self.app.detail("T03")["reference"]["sha256"], bundled_sha)
        rows = self.app.reference_library_list()["references"]
        families = {row["family"] for row in rows if row["status"] == "active"}
        self.assertEqual(families, {"nda", "customer_order"})

    def test_withdrawing_selected_nda_restores_bundled_baseline_for_new_uploads(self):
        nda_data = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        result = self.app.upload_reference(nda_data, "fictional-mutual-nda.docx")
        item = result["library_item"]
        self.assertEqual(self.app.active_reference_sha256, item["sha256"])
        self.app.update_reference_status(item["reference_id"], "withdrawn", "Fictional Legal team withdrawal for test")
        self.assertEqual(self.app.active_reference_sha256, self.app.bundled_reference_sha256)
        self.assertEqual(self.app.reference_info()["current"]["sha256"], self.app.bundled_reference_sha256)
        self.assertNotIn(item["sha256"], {row["sha256"] for row in self.app.reference_info()["available"]})
        with self.assertRaisesRegex(ValueError, "cannot be selected"):
            self.app.select_reference(item["sha256"])

    def test_superseded_and_withdrawn_are_durable_and_excluded_from_new_matches(self):
        data = new_customer_order_bytes()
        item = self.app.upload_reference(data, CUSTOMER_ORDER.name)["library_item"]
        changed = self.app.update_reference_status(item["reference_id"], "withdrawn", "Fictional Legal team withdrawal for test")
        self.assertEqual(changed["status"], "withdrawn")
        self.assertEqual(changed["status_history"][-1]["from"], "active")
        proposal = self.app.match_reference(data, "incoming-order.docx")["proposal"]
        self.assertIn(item["reference_id"], {entry["reference_id"] for entry in proposal["excluded"]})
        self.assertNotEqual((proposal.get("proposal") or {}).get("reference_id"), item["reference_id"])

        restarted = App(ROOT, self.state)
        restored = restarted.reference_library_detail(item["reference_id"])
        self.assertEqual(restored["status"], "withdrawn")
        self.assertEqual(restored["status_history"], changed["status_history"])
        self.assertEqual(restored["source_integrity"], "verified")
        self.assertEqual((self.state / "references" / (item["sha256"] + ".docx")).read_bytes(), data)

    def test_pre_governance_pr11_upload_migrates_to_active_with_auditable_history(self):
        item = self.app.upload_reference(new_customer_order_bytes(), "fictional-order.docx")["library_item"]
        meta_path = self.state / "references" / (item["sha256"] + ".json")
        metadata = json.loads(meta_path.read_text())
        metadata["status"] = "registered_for_evaluation"
        metadata["approval_status"] = "unapproved"
        metadata["record_sha256"] = hashlib.sha256(json.dumps({key: value for key, value in metadata.items() if key != "record_sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False))

        migrated = App(ROOT, self.state).reference_library_detail(item["reference_id"])
        self.assertEqual(migrated["status"], "active")
        self.assertEqual(migrated["status_history"][-1]["from"], "registered_for_evaluation")
        persisted = json.loads(meta_path.read_text())
        self.assertEqual(persisted["status"], "active")
        self.assertNotIn("approval_status", persisted)
        self.assertEqual(persisted["record_sha256"], hashlib.sha256(json.dumps({key: value for key, value in persisted.items() if key != "record_sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest())

    def test_matching_proposal_snapshot_survives_restart_with_source_and_identity(self):
        standard = self.app.upload_reference(new_customer_order_bytes(13), "fictional-direct-desktop.docx")["library_item"]
        incoming = new_customer_order_bytes(14)
        record = self.app.match_reference(incoming, "incoming-direct-desktop.docx")
        self.assertEqual(record["proposal"]["human_confirmation_required"], True)
        self.assertFalse(record["proposal"]["comparison_allowed"])
        self.assertEqual(record["human_decision"]["status"], "pending")
        self.assertEqual(record["comparison"]["status"], "not_run")
        self.assertIn(standard["reference_id"], {record["proposal"].get("proposal", {}).get("reference_id"), *[row["reference_id"] for row in record["proposal"].get("alternatives", [])]})

        restarted = App(ROOT, self.state)
        restored = restarted.reference_match_detail(record["incoming"]["sha256"])
        self.assertEqual(restored["proposal"], record["proposal"])
        self.assertEqual(restored["incoming"], record["incoming"])
        self.assertEqual((self.state / "reference_matches" / (record["incoming"]["sha256"] + ".docx")).read_bytes(), incoming)

    def test_corrupt_and_unsupported_nda_references_are_rejected_clearly(self):
        with self.assertRaisesRegex(ValueError, "Reference extraction is incomplete"):
            self.app.upload_reference(b"not a DOCX", "broken.docx")
        missing_clause = (ROOT / "dataset/incoming/T04-missing-no-licence.docx").read_bytes()
        with self.assertRaisesRegex(ValueError, "missing clause headings"):
            self.app.upload_reference(missing_clause, "unsupported-nda.docx")

    def test_tampering_is_visible_in_listing_and_withheld_from_detail_and_original(self):
        data = new_customer_order_bytes()
        item = self.app.upload_reference(data, CUSTOMER_ORDER.name)["library_item"]
        source = self.state / "references" / (item["sha256"] + ".docx")
        source.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "unavailable or changed"):
            self.app.upload_reference(data, CUSTOMER_ORDER.name)
        listed = next(row for row in self.app.reference_library_list()["references"] if row["reference_id"] == item["reference_id"])
        self.assertEqual(listed["source_integrity"], "mismatch")
        with self.assertRaisesRegex(ValueError, "source content is withheld"):
            self.app.reference_library_detail(item["reference_id"])
        with self.assertRaisesRegex(ValueError, "Reference recovery required"):
            App(ROOT, self.state)

    def test_metadata_tampering_cannot_implicitly_approve_an_uploaded_standard(self):
        item = self.app.upload_reference(new_customer_order_bytes(), "fictional-order.docx")["library_item"]
        meta_path = self.state / "references" / (item["sha256"] + ".json")
        metadata = json.loads(meta_path.read_text())
        metadata["approval_status"] = "approved"
        meta_path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "metadata integrity mismatch"):
            App(ROOT, self.state)


def item_document_units(data: bytes, filename: str):
    from chug.document import extract
    return extract(data, filename)["units"]


class ReferenceLibraryApiTests(unittest.TestCase):
    def test_library_detail_and_original_are_read_only_and_source_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            Handler.app = App(ROOT, Path(directory))
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            try:
                listing = json.loads(urlopen(base + "/api/reference-library").read())
                candidate = next(row for row in listing["references"] if row["reference_id"] == "ORDER-PRO-DIRECT")
                detail = json.loads(urlopen(base + "/api/reference-library/ORDER-PRO-DIRECT").read())
                original = urlopen(base + detail["original_url"]).read()
                self.assertEqual(candidate["status"], "research_candidate")
                self.assertEqual(detail["family"], "customer_order")
                self.assertEqual(hashlib.sha256(original).hexdigest(), detail["sha256"])

                upload_bytes = new_customer_order_bytes()
                boundary = "reference-library-boundary"
                multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="Uploaded Order.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + upload_bytes + (f'\r\n--{boundary}--\r\n').encode()
                request = Request(base + "/api/reference/upload", data=multipart, method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
                uploaded = json.loads(urlopen(request).read())
                self.assertEqual(uploaded["library_item"]["family"], "customer_order")
                self.assertEqual(uploaded["library_item"]["status"], "active")
                self.assertEqual(uploaded["current"]["sha256"], Handler.app.bundled_reference_sha256)
                self.assertEqual(hashlib.sha256(urlopen(base + uploaded["library_item"]["original_url"]).read()).hexdigest(), uploaded["library_item"]["sha256"])
                request = Request(base + "/api/reference-library", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_matching_api_persists_applicability_snapshot_and_status_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            Handler.app = App(ROOT, state)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:" + str(server.server_port)
            boundary = "matching-api-boundary"
            try:
                standard_data = new_customer_order_bytes(13)
                standard_request = Request(base + "/api/reference/upload", data=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="Direct standard.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + standard_data + (f'\r\n--{boundary}--\r\n').encode(), method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
                standard = json.loads(urlopen(standard_request).read())["library_item"]
                incoming_data = new_customer_order_bytes(14)
                match_request = Request(base + "/api/reference-matches", data=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="Incoming order.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + incoming_data + (f'\r\n--{boundary}--\r\n').encode(), method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
                result = json.loads(urlopen(match_request).read())
                self.assertEqual(result["incoming"]["sha256"], hashlib.sha256(incoming_data).hexdigest())
                self.assertTrue(result["proposal"]["human_confirmation_required"])
                self.assertFalse(result["proposal"]["comparison_allowed"])
                self.assertEqual(result["comparison"]["status"], "not_run")
                self.assertEqual(result["human_decision"]["status"], "pending")
                detailed = json.loads(urlopen(base + "/api/reference-matches/" + result["incoming"]["sha256"]).read())
                self.assertEqual(detailed["proposal"], result["proposal"])
                self.assertIn(standard["reference_id"], {detailed["proposal"].get("proposal", {}).get("reference_id"), *[row["reference_id"] for row in detailed["proposal"].get("alternatives", [])]})
                self.assertEqual(urlopen(base + detailed["original_url"]).read(), incoming_data)

                status_request = Request(base + "/api/reference-library/" + standard["reference_id"] + "/status", data=json.dumps({"status": "superseded", "reason": "New fictional version replaces it"}).encode(), method="POST", headers={"Content-Type": "application/json"})
                status = json.loads(urlopen(status_request).read())
                self.assertEqual(status["status"], "superseded")
                Handler.app = App(ROOT, state)
                self.assertEqual(Handler.app.reference_library_detail(standard["reference_id"])["status"], "superseded")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
