from __future__ import annotations

import hashlib
import io
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pypdf import PdfReader, PdfWriter

from chug.document import extract, extract_file, media_type_for, source_extension
from chug.server import App, Handler


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DOCX = ROOT / "dataset/incoming/T02-known-term-change.docx"


def make_pdf(pages: list[list[str]]) -> bytes:
    """Build a small deterministic text PDF without adding a fixture generator dependency."""
    objects = [b"", b"<< /Type /Catalog /Pages 2 0 R >>", None,
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []
    for lines in pages:
        page_id = len(objects)
        content_id = page_id + 1
        page_ids.append(page_id)
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode())
        commands = ["BT", "/F1 9 Tf", "50 780 Td"]
        for index, line in enumerate(lines):
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({safe}) Tj")
            if index != len(lines) - 1:
                commands.append("0 -13 Td")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, payload in enumerate(objects[1:], 1):
        offsets.append(len(out))
        out.extend(f"{object_id} 0 obj\n".encode() + payload + b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def as_pdf(document: dict) -> bytes:
    units = [unit["text"] for unit in document["units"]]
    pages = [units[index:index + 48] for index in range(0, len(units), 48)]
    return make_pdf(pages or [[""]])


def multipart(filename: str, payload: bytes) -> tuple[bytes, str]:
    boundary = "pdf-upload-boundary"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    return body, "multipart/form-data; boundary=" + boundary


class PdfExtractionTests(unittest.TestCase):
    def test_docx_and_pdf_share_family_matching_and_pdf_provision_anchors(self):
        baseline_bytes = REFERENCE_DOCX.read_bytes()
        baseline_doc = extract_file(REFERENCE_DOCX)
        reference_pdf = as_pdf(baseline_doc)
        incoming_doc = {**baseline_doc, "units": [dict(unit) for unit in baseline_doc["units"]]}
        target = next(unit for unit in incoming_doc["units"] if "five years" in unit["text"])
        target["text"] = target["text"].replace("five years", "seven years")
        incoming_pdf = as_pdf(incoming_doc)

        docx = extract(baseline_bytes, "baseline.docx")
        pdf_reference = extract(reference_pdf, "baseline.pdf")
        self.assertEqual(docx["coverage"]["status"], "complete")
        self.assertEqual(pdf_reference["coverage"]["status"], "complete", pdf_reference["coverage"]["issues"])
        self.assertTrue(all(unit["anchor"].startswith("pdf:p") for unit in pdf_reference["units"]))
        self.assertEqual(pdf_reference["sha256"], hashlib.sha256(reference_pdf).hexdigest())

        with tempfile.TemporaryDirectory() as directory:
            app = App(ROOT, Path(directory))
            registered = app.upload_reference(reference_pdf, "fictional-nda-reference.pdf")["library_item"]
            self.assertEqual(registered["status"], "active")
            docx_match = app.match_reference(baseline_bytes, "incoming.docx")
            pdf_match = app.match_reference(incoming_pdf, "incoming.pdf")
            self.assertEqual(docx_match["proposal"]["status"], "proposed")
            self.assertEqual(pdf_match["proposal"]["status"], "proposed")
            self.assertEqual(pdf_match["proposal"]["context"]["dimensions"]["family"]["value"], "nda")
            pdf_intake = app.intake(incoming_pdf, "incoming.pdf")
            self.assertEqual(pdf_intake["route"], "review_required")
            changed = [finding for finding in pdf_intake["comparison"]["findings"] if finding["category"] == "changed_clause"]
            self.assertTrue(changed)
            self.assertTrue(any(source["anchor"].startswith("pdf:p") for source in changed[0]["sources"]))
            self.assertEqual((Path(directory) / "intakes" / (pdf_intake["incoming"]["sha256"] + ".pdf")).read_bytes(), incoming_pdf)

    def test_non_text_and_malformed_pdfs_fail_closed_and_mismatch_is_detected(self):
        image_only = extract(make_pdf([[]]), "scan.pdf")
        self.assertEqual(image_only["coverage"]["status"], "blocked")
        self.assertEqual(image_only["coverage"]["reason"], "needs_ocr")
        self.assertEqual(image_only["units"], [])
        ambiguous_table = extract(make_pdf([["Clause 1    Second column value"]]), "table.pdf")
        self.assertEqual(ambiguous_table["coverage"]["status"], "blocked")
        self.assertTrue(any("table-like" in issue for issue in ambiguous_table["coverage"]["issues"]))
        malformed = extract(b"%PDF-1.4\nnot a valid PDF", "broken.pdf")
        self.assertEqual(malformed["coverage"]["status"], "blocked")
        mismatch = extract(make_pdf([["This Mutual Non-Disclosure Agreement"]]), "wrong.docx")
        self.assertEqual(mismatch["coverage"]["status"], "blocked")
        self.assertEqual(source_extension(mismatch), ".pdf")
        self.assertEqual(media_type_for(mismatch), "application/pdf")
        self.assertTrue(any("extension" in issue for issue in mismatch["coverage"]["issues"]))
        too_large = extract(make_pdf([["Text"]]) + b" " * 2_000_001, "large.pdf")
        self.assertEqual(too_large["coverage"]["reason"], "too_large")

    def test_encrypted_and_excessive_page_pdfs_block(self):
        plain = PdfReader(io.BytesIO(make_pdf([["A synthetic NDA"]])))
        writer = PdfWriter()
        writer.add_page(plain.pages[0])
        writer.encrypt("secret")
        encrypted = io.BytesIO()
        writer.write(encrypted)
        blocked = extract(encrypted.getvalue(), "encrypted.pdf")
        self.assertEqual(blocked["coverage"]["status"], "blocked")
        self.assertEqual(blocked["coverage"]["reason"], "encrypted")
        too_many = extract(make_pdf([["Text"] for _ in range(101)]), "long.pdf")
        self.assertEqual(too_many["coverage"]["reason"], "too_many_pages")

    def test_pdf_intake_restarts_and_returns_exact_pdf_media_type(self):
        document = extract_file(REFERENCE_DOCX)
        data = as_pdf(document)
        with tempfile.TemporaryDirectory() as directory:
            app = App(ROOT, Path(directory))
            reference = app.upload_reference(data, "fictional-reference.pdf")["library_item"]
            result = app.intake(data, "fictional incoming.pdf")
            digest = result["incoming"]["sha256"]
            restarted = App(ROOT, Path(directory))
            self.assertEqual(restarted.intake_detail(digest)["document"]["format"], "pdf")
            Handler.app = restarted
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body, content_type = multipart("incoming.pdf", data)
                response = urlopen(Request(f"http://127.0.0.1:{server.server_port}/api/intakes", data=body, headers={"Content-Type": content_type}, method="POST"))
                self.assertEqual(response.status, 201)
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/intakes/{digest}/original") as downloaded:
                    self.assertEqual(downloaded.headers.get_content_type(), "application/pdf")
                    self.assertTrue(downloaded.headers.get_filename().endswith(".pdf"))
                    self.assertEqual(downloaded.read(), data)
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/reference-library/{reference['reference_id']}/original") as downloaded:
                    self.assertEqual(downloaded.headers.get_content_type(), "application/pdf")
                    self.assertTrue(downloaded.headers.get_filename().endswith(".pdf"))
                    self.assertEqual(downloaded.read(), data)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
