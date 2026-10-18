"""Synthetic A/B/C lifecycle for comparison feedback, not legal accuracy."""
from __future__ import annotations

import tempfile
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from chug.server import App, Handler

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "dataset/learning"


class ComparisonCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.app = App(ROOT, self.state)

    def upload(self, name):
        return self.app.upload((LEARNING / name).read_bytes(), name)

    def test_a_b_c_authorised_lesson_and_withdrawal(self):
        # A = restricted regulatory archive, B = differently worded archive,
        # C = superficially similar archive with commercial analytics access.
        a = self.upload("L01-audit-retention.docx")
        b = self.upload("L03-regulatory-records.docx")
        c = self.upload("L02-analytics-retention.docx")
        before_b = self.app.detail(b)
        before_c = self.app.detail(c)
        self.assertEqual(before_b["analysis"]["route"], "review_required")
        self.assertEqual(before_c["analysis"]["route"], "review_required")
        self.assertEqual(before_b["analysis"]["comparison_lessons"], [])
        first = self.app.detail(a)
        finding = next(row for row in first["analysis"]["findings"] if row["title"] == "Changed: Return or Destruction")
        correction = self.app.record_correction(a, finding["id"], finding["sources"][0]["anchor"], finding["reference"]["anchor"], "partial_overlap", "Archive exception remains only for a named retention duty; check who may access it and whether business use is excluded.", "Fictional reviewer")
        self.assertEqual(self.app.detail(b)["analysis"]["comparison_lessons"], [])
        self.assertEqual(self.app.detail(a)["history"], [])  # Distinct from legal decisions.
        self.assertEqual(self.app.detail(a)["corrections"][0]["id"], correction["id"])
        publication = self.app.publish_correction(correction["id"], "Fictional demo publisher", "Regulatory archive with no business access", "Check the actual duty, duration and access on each new NDA")
        after_b = self.app.detail(b)
        after_c = self.app.detail(c)
        self.assertTrue(any(row["publication_id"] == publication["id"] for row in after_b["analysis"]["comparison_lessons"]))
        self.assertTrue(any(row["publication_id"] == publication["id"] for row in after_c["analysis"]["comparison_lessons"]))
        self.assertEqual(after_b["analysis"]["route"], before_b["analysis"]["route"])
        self.assertEqual(after_c["analysis"]["route"], before_c["analysis"]["route"])
        self.assertIn("commercial team", after_c["analysis"]["findings"][0]["sources"][0]["text"])
        self.assertEqual(after_c["analysis"]["comparison_lessons"][0]["applicability"], "unverified; compare the current exception and commercial context")
        restarted = App(ROOT, self.state)
        self.assertTrue(restarted.detail(b)["analysis"]["comparison_lessons"])
        self.app.corrections.withdraw(publication["id"], "Fictional demo publisher", "Withdrawn for review")
        self.assertEqual(self.app.detail(b)["analysis"]["comparison_lessons"], [])
        self.assertEqual(self.app.detail(a)["corrections"][0]["publications"][0]["status"], "withdrawn")
        self.assertEqual(App(ROOT, self.state).detail(c)["analysis"]["comparison_lessons"], [])

    def test_invalid_anchor_and_tampered_published_source_fail_closed(self):
        a = self.upload("L01-audit-retention.docx")
        finding = next(row for row in self.app.detail(a)["analysis"]["findings"] if row["title"] == "Changed: Return or Destruction")
        with self.assertRaisesRegex(ValueError, "valid source"):
            self.app.record_correction(a, finding["id"], "invented", finding["reference"]["anchor"], "unsure", "Check this", "Fictional reviewer")
        correction = self.app.record_correction(a, finding["id"], finding["sources"][0]["anchor"], finding["reference"]["anchor"], "partial_overlap", "Check the archive access", "Fictional reviewer")
        self.app.publish_correction(correction["id"], "Fictional publisher", "Regulatory archive", "Check access")
        source = self.state / "uploads" / (self.app.detail(a)["document"]["sha256"] + ".docx")
        source.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "source identity mismatch"):
            App(ROOT, self.state)

    def test_http_history_and_correction_round_trip(self):
        Handler.app = self.app
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = "http://127.0.0.1:%d" % server.server_port

        def get(path):
            with urllib.request.urlopen(base + path) as response:
                return json.load(response)

        def post(path, body):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request) as response:
                return json.load(response)

        history = get("/api/history/H02")
        self.assertEqual(history["decision"]["decision"], "accepted_with_conditions")
        self.assertEqual(history["document"]["sha256"], self.app.historical["H02"]["sha256"])
        with urllib.request.urlopen(base + "/api/history/H02/original") as response:
            self.assertEqual(response.headers.get_content_type(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            import hashlib
            self.assertEqual(hashlib.sha256(response.read()).hexdigest(), history["document"]["sha256"])
        self.assertTrue(any(row["match_basis"] == "exact wording" for row in get("/api/contracts/T02")["analysis"]["precedents"]))

        a = self.upload("L01-audit-retention.docx")
        b = self.upload("L03-regulatory-records.docx")
        finding = next(row for row in get("/api/contracts/" + a)["analysis"]["findings"] if row["title"] == "Changed: Return or Destruction")
        correction = post("/api/corrections", {"document_id": a, "finding_id": finding["id"], "source_anchor": finding["sources"][0]["anchor"], "reference_anchor": finding["reference"]["anchor"], "relationship": "partial_overlap", "explanation": "Check whether any business team can access the retained copy.", "reviewer": "Fictional reviewer"})
        self.assertEqual(get("/api/contracts/" + b)["analysis"]["comparison_lessons"], [])
        publication = post("/api/correction-lessons", {"correction_id": correction["id"], "publisher": "Fictional publisher", "context": "Restricted regulatory archive", "reuse_limits": "Check the specific duty and access", "role": "demo_legal_reviewer", "acknowledged": True})
        self.assertTrue(any(row["publication_id"] == publication["id"] for row in get("/api/contracts/" + b)["analysis"]["comparison_lessons"]))
        post("/api/correction-lessons/" + publication["id"] + "/withdraw", {"actor": "Fictional publisher", "reason": "Retract the lesson", "role": "demo_legal_reviewer", "acknowledged": True})
        self.assertEqual(get("/api/contracts/" + b)["analysis"]["comparison_lessons"], [])

    def test_reported_missed_provision_blocks_routine_route(self):
        before = self.app.detail("T01")
        self.assertEqual(before["analysis"]["route"], "routine_candidate")
        self.assertEqual(before["analysis"]["findings"], [])
        source = next(unit for unit in before["document"]["units"] if "Confidential Information" in unit["text"])
        correction = self.app.record_correction("T01", "", source["anchor"], "", "overlooked_exception", "Fictional reviewer wants this definition checked against a separate schedule.", "Fictional reviewer")
        self.assertIsNone(correction["finding_id"])
        after = self.app.detail("T01")
        self.assertEqual(after["analysis"]["route"], "review_required")
        self.assertEqual(after["analysis"]["reason"], "Reviewer reported a possibly missed exception")
        self.assertEqual(after["history"], [])
        self.assertEqual(App(ROOT, self.state).detail("T01")["analysis"]["route"], "review_required")


if __name__ == "__main__":
    unittest.main()
