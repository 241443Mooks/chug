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


def new_customer_order_bytes():
    """Create a distinct synthetic upload from the research specimen without touching it."""
    source = CUSTOMER_ORDER.read_bytes()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as updated:
        for entry in original.infolist():
            content = original.read(entry.filename)
            if entry.filename == "word/document.xml":
                content = content.replace(b"12 named desktop software users", b"13 named desktop software users")
            updated.writestr(entry, content)
    return output.getvalue()


class ReferenceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.app = App(ROOT, self.state)

    def tearDown(self):
        self.temp.cleanup()

    def test_customer_order_reference_persists_as_unapproved_without_changing_nda(self):
        data = new_customer_order_bytes()
        baseline = self.app.active_reference_sha256
        item = self.app.upload_reference(data, CUSTOMER_ORDER.name)["library_item"]
        digest = hashlib.sha256(data).hexdigest()

        self.assertEqual(item["family"], "customer_order")
        self.assertEqual(item["sha256"], digest)
        self.assertEqual(item["approval_status"], "unapproved")
        self.assertEqual(item["status"], "registered_for_evaluation")
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
        self.assertEqual(duplicate["approval_status"], "unapproved")
        self.assertEqual(len(list((self.state / "references").glob("*.docx"))), 1)

    def test_supported_nda_upload_retains_existing_selection_behavior_and_family_isolation(self):
        customer_data = new_customer_order_bytes()
        self.app.upload_reference(customer_data, CUSTOMER_ORDER.name)
        bundled_sha = self.app.bundled_reference_sha256
        nda_data = (ROOT / "dataset/incoming/T02-known-term-change.docx").read_bytes()
        result = self.app.upload_reference(nda_data, "fictional-mutual-nda.docx")

        self.assertEqual(result["library_item"]["family"], "nda")
        self.assertEqual(result["library_item"]["approval_status"], "unapproved")
        self.assertEqual(result["current"]["sha256"], hashlib.sha256(nda_data).hexdigest())
        self.assertNotEqual(self.app.active_reference_sha256, bundled_sha)
        self.assertEqual(self.app.detail("T03")["reference"]["sha256"], bundled_sha)
        rows = self.app.reference_library_list()["references"]
        families = {row["family"] for row in rows if row["status"] == "registered_for_evaluation"}
        self.assertEqual(families, {"nda", "customer_order"})

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
                self.assertEqual(candidate["approval_status"], "unapproved")
                self.assertEqual(detail["family"], "customer_order")
                self.assertEqual(hashlib.sha256(original).hexdigest(), detail["sha256"])

                upload_bytes = new_customer_order_bytes()
                boundary = "reference-library-boundary"
                multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="Uploaded Order.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + upload_bytes + (f'\r\n--{boundary}--\r\n').encode()
                request = Request(base + "/api/reference/upload", data=multipart, method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary})
                uploaded = json.loads(urlopen(request).read())
                self.assertEqual(uploaded["library_item"]["family"], "customer_order")
                self.assertEqual(uploaded["library_item"]["approval_status"], "unapproved")
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


if __name__ == "__main__":
    unittest.main()
