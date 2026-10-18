from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from chug.document import extract_file
from chug.server import App, Handler

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "dataset/learning"


class LearningLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        Handler.app = App(ROOT, self.state)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return json.load(response)

    def post(self, path, body):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def upload(self, filename):
        data = (LEARNING / filename).read_bytes()
        boundary = "chug-learning-boundary"
        multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n').encode() + data + (f'\r\n--{boundary}--\r\n').encode()
        request = urllib.request.Request(self.base + "/api/upload", data=multipart, headers={"Content-Type": "multipart/form-data; boundary=" + boundary}, method="POST")
        with urllib.request.urlopen(request) as response:
            document_id = json.load(response)["id"]
        self.assertEqual(self.get("/api/contracts/" + document_id)["document"]["sha256"], hashlib.sha256(data).hexdigest())
        return document_id

    def test_published_decision_helps_later_review_then_withdraws(self):
        for name in ("L01-audit-retention.docx", "L02-analytics-retention.docx"):
            self.assertEqual(extract_file(LEARNING / name)["coverage"]["status"], "complete")
        first = self.upload("L01-audit-retention.docx")
        second = self.upload("L02-analytics-retention.docx")
        first_detail = self.get("/api/contracts/" + first)
        second_before = self.get("/api/contracts/" + second)
        self.assertEqual(first_detail["analysis"]["route"], "review_required")
        self.assertEqual(second_before["analysis"]["route"], "review_required")
        self.assertFalse(any(p.get("kind") == "published_demo" for p in second_before["analysis"]["precedents"]))

        finding = next(f for f in first_detail["analysis"]["findings"] if f["title"] == "Changed: Return or Destruction")
        decision = self.post("/api/decisions", {"document_id": first, "reviewer": "Demo legal reviewer", "decision": "approve", "rationale": "Audit retention is acceptable only with restricted access.", "conditions": "Named regulatory duty; compliance access only; annual deletion review.", "finding_ids": [finding["id"]]})
        self.assertEqual(decision["considered_sources"], [{"finding_id": finding["id"], "anchor": finding["sources"][0]["anchor"], "text": finding["sources"][0]["text"]}])
        # A recorded approval is private history until a separate publication event.
        self.assertFalse(any(p.get("kind") == "published_demo" for p in self.get("/api/contracts/" + second)["analysis"]["precedents"]))
        publication_body = {"document_id": first, "decision_id": decision["id"], "source_anchor": finding["sources"][0]["anchor"], "authoriser": "Demo legal reviewer", "context": "Regulated audit retention; archive unavailable to business users.", "reuse_limits": "Check the actual retention duty and access controls. Never treat this as general approval.", "role": "demo_legal_reviewer", "acknowledged": True}
        with self.assertRaises(urllib.error.HTTPError) as invalid:
            self.post("/api/precedents", {**publication_body, "acknowledged": False})
        self.assertEqual(invalid.exception.code, 400)
        publication = self.post("/api/precedents", publication_body)
        self.assertEqual(publication["decision_id"], decision["id"])
        self.assertEqual(publication["source_text"], finding["sources"][0]["text"])
        with self.assertRaises(urllib.error.HTTPError) as duplicate_publication:
            self.post("/api/precedents", publication_body)
        self.assertEqual(duplicate_publication.exception.code, 400)

        second_after = self.get("/api/contracts/" + second)
        self.assertEqual(second_after["analysis"]["route"], "review_required")
        found = next(p for p in second_after["analysis"]["precedents"] if p.get("publication_id") == publication["id"])
        self.assertEqual(found["conditions"], decision["conditions"])
        self.assertIn("Regulated audit retention", found["context"])
        self.assertIn("Check the actual retention duty", found["reuse_authority"])
        self.assertIn("Check context and conditions", found["why_retrieved"])
        self.assertEqual(len(second_after["history"]), 0)
        self.assertFalse(any(p.get("publication_id") == publication["id"] for p in self.get("/api/contracts/" + first)["analysis"]["precedents"]))
        second_decision = self.post("/api/decisions", {"document_id": second, "reviewer": "Second reviewer", "decision": "request_amendment", "rationale": "Commercial-team access differs from the audit-only case.", "finding_ids": [second_after["analysis"]["findings"][0]["id"]]})
        self.assertEqual(self.get("/api/contracts/" + second)["history"][-1]["id"], second_decision["id"])

        restarted = App(ROOT, self.state)
        self.assertTrue(any(p.get("publication_id") == publication["id"] for p in restarted.detail(second)["analysis"]["precedents"]))
        withdrawal = self.post("/api/precedents/" + publication["id"] + "/withdraw", {"actor": "Demo legal reviewer", "reason": "The conditions were superseded.", "role": "demo_legal_reviewer", "acknowledged": True})
        self.assertEqual(withdrawal["publication_id"], publication["id"])
        self.assertFalse(any(p.get("publication_id") == publication["id"] for p in self.get("/api/contracts/" + second)["analysis"]["precedents"]))
        history = self.get("/api/contracts/" + first)["publications"]
        self.assertEqual(history[0]["status"], "withdrawn")
        self.assertEqual(history[0]["withdrawal"]["reason"], "The conditions were superseded.")
        after_restart = App(ROOT, self.state)
        self.assertEqual(len(after_restart.detail(first)["history"]), 1)
        self.assertFalse(any(p.get("publication_id") == publication["id"] for p in after_restart.detail(second)["analysis"]["precedents"]))
        with self.assertRaises(urllib.error.HTTPError) as duplicate:
            self.post("/api/precedents/" + publication["id"] + "/withdraw", {"actor": "Demo legal reviewer", "reason": "Again", "role": "demo_legal_reviewer", "acknowledged": True})
        self.assertEqual(duplicate.exception.code, 400)

    def test_publication_requires_valid_decision_evidence_and_intact_source(self):
        first = self.upload("L01-audit-retention.docx")
        detail = self.get("/api/contracts/" + first)
        finding = detail["analysis"]["findings"][0]
        decision = self.post("/api/decisions", {"document_id": first, "reviewer": "Demo", "decision": "request_amendment", "rationale": "Need narrower retention.", "finding_ids": []})
        body = {"document_id": first, "decision_id": decision["id"], "source_anchor": finding["sources"][0]["anchor"], "authoriser": "Demo", "context": "Audit retention", "reuse_limits": "Assess independently", "role": "demo_legal_reviewer", "acknowledged": True}
        with self.assertRaises(urllib.error.HTTPError) as invalid:
            self.post("/api/precedents", body)
        self.assertEqual(invalid.exception.code, 400)
        source = self.state / "uploads" / (detail["document"]["sha256"] + ".docx")
        source.write_bytes(b"tampered")
        with self.assertRaises(urllib.error.HTTPError) as damaged:
            self.post("/api/precedents", body)
        self.assertEqual(damaged.exception.code, 400)

    def test_broken_publication_log_fails_closed_on_restart(self):
        path = self.state / "knowledge.jsonl"
        path.write_text('{"type":"publish","id":"broken"}\n')
        with self.assertRaisesRegex(ValueError, "invalid publication"):
            App(ROOT, self.state)

    def test_publication_cannot_be_relinked_to_an_unconsidered_source(self):
        app = App(ROOT, self.state)
        document_id = app.upload((LEARNING / "L01-audit-retention.docx").read_bytes(), "L01.docx")
        detail = app.detail(document_id)
        finding = detail["analysis"]["findings"][0]
        source = finding["sources"][0]
        decision = app.ledger.append(detail["document"]["sha256"], detail["document"]["filename"], "Demo", "approve", "Restricted audit retention only.", [finding["id"]], "Compliance access only", [{"finding_id": finding["id"], "anchor": source["anchor"], "text": source["text"]}])
        app.publish(document_id, decision["id"], source["anchor"], "Demo", "Regulated audit retention", "Check duty and access")
        path = self.state / "knowledge.jsonl"
        publication = json.loads(path.read_text())
        other = next(unit for unit in detail["document"]["units"] if unit["anchor"] == "word/document.xml:p20")
        publication["source_anchor"] = other["anchor"]
        publication["source_text"] = other["text"]
        publication["section_title"] = "No Licence"
        path.write_text(json.dumps(publication) + "\n")
        with self.assertRaisesRegex(ValueError, "reviewed evidence"):
            App(ROOT, self.state)


if __name__ == "__main__":
    unittest.main()
