"""Integration contract for the reviewer-facing customer-order boundary."""
from pathlib import Path
import unittest

from chug.customer_order_review import CustomerOrderReview
from chug.document import extract_file


ROOT = Path(__file__).resolve().parents[1]
ORDER = ROOT / "research/reference-library-v0.1/routine-clients/C009 - Inverlea Media Ltd.docx"
NDA = ROOT / "research/reference-library-v0.1/incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx"
UNCLEAR_ORDER = ROOT / "research/reference-library-v0.1/incoming-tests/Incoming - Ambiguous Reseller Cloud Scan Purchase.docx"


class CustomerOrderReviewIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = CustomerOrderReview(ROOT)

    def confirmation(self, candidate):
        return {
            "confirmed": True,
            "reference_id": candidate["reference_id"],
            "sha256": candidate["sha256"],
            "reviewer": "Synthetic integration reviewer",
            "timestamp": "2026-10-13T10:00:00Z",
            "rationale": "Checked the order scope against the proposed source.",
        }

    def test_reference_proposal_confirmation_and_comparison_are_separate(self):
        incoming = extract_file(ORDER)
        prepared = self.service.prepare(incoming)

        self.assertEqual(prepared["reference_proposal"]["status"], "proposed_with_gaps")
        self.assertTrue(prepared["eligible_candidates"])
        self.assertEqual(prepared["reference_confirmation"]["status"], "pending")
        self.assertEqual(prepared["comparison"]["status"], "not_run")
        self.assertEqual(prepared["human_decision"]["status"], "pending")

        candidate = prepared["eligible_candidates"][0]
        result = self.service.compare(incoming, candidate["reference_id"], self.confirmation(candidate))

        self.assertEqual(result["reference_confirmation"]["status"], "confirmed")
        self.assertEqual(result["comparison"]["status"], "complete")
        self.assertTrue(result["comparison"]["observations"])
        self.assertEqual(result["routing"]["route"], "review_required")
        self.assertEqual(result["human_decision"], {"status": "pending", "required": True, "outcome": None})
        self.assertFalse(result["comparison"]["approved"])

        known_incoming = {unit["anchor"]: unit["text"] for unit in incoming["units"]}
        selected = self.service.order_references[candidate["reference_id"]]
        known_reference = {unit["anchor"]: unit["text"] for unit in selected["document"]["units"]}
        for observation in result["comparison"]["observations"]:
            self.assertIn("difference_type", observation)
            self.assertIn("uncertainty", observation)
            for passage in observation["incoming_passages"]:
                self.assertEqual(known_incoming[passage["anchor"]], passage["text"])
            for passage in observation["reference_passages"]:
                self.assertEqual(known_reference[passage["anchor"]], passage["text"])

    def test_missing_confirmation_and_wrong_deployment_never_compare(self):
        incoming = extract_file(ORDER)
        prepared = self.service.prepare(incoming)
        eligible = prepared["eligible_candidates"][0]

        no_confirmation = self.service.compare(incoming, eligible["reference_id"], {})
        self.assertEqual(no_confirmation["comparison"]["status"], "not_run")
        self.assertEqual(no_confirmation["routing"]["status"], "confirmation_required")

        wrong_deployment = next(
            reference for reference in self.service.order_references.values()
            if reference["deployment"] != self.service.order_references[eligible["reference_id"]]["deployment"]
        )
        wrong = self.service.compare(incoming, wrong_deployment["reference_id"], self.confirmation(wrong_deployment))
        self.assertEqual(wrong["comparison"]["status"], "not_run")
        self.assertEqual(wrong["routing"]["status"], "reference_not_eligible")

    def test_wrong_family_missing_context_and_incomplete_extraction_abstain(self):
        nda = extract_file(NDA)
        wrong_family = self.service.prepare(nda)
        self.assertEqual(wrong_family["eligible_candidates"], [])
        self.assertEqual(wrong_family["reference_proposal"]["status"], "wrong_family")
        self.assertEqual(wrong_family["comparison"]["status"], "not_run")

        # A family-specific reference cannot be forced through on an NDA source.
        selected = next(iter(self.service.order_references.values()))
        forced = self.service.compare(nda, selected["reference_id"], self.confirmation(selected))
        self.assertEqual(forced["comparison"]["status"], "not_run")

        missing_context = self.service.prepare(extract_file(UNCLEAR_ORDER))
        self.assertEqual(missing_context["applicability"]["status"], "needs_context")
        self.assertEqual(missing_context["eligible_candidates"], [])
        self.assertEqual(missing_context["comparison"]["status"], "not_run")

        incomplete = {**extract_file(ORDER), "coverage": {"status": "blocked"}}
        blocked = self.service.prepare(incomplete)
        self.assertEqual(blocked["routing"]["route"], "blocked_extraction")
        self.assertEqual(blocked["eligible_candidates"], [])

    def test_ambiguous_heading_is_reported_without_invented_alignment(self):
        incoming = extract_file(ORDER)
        prepared = self.service.prepare(incoming)
        candidate = prepared["eligible_candidates"][0]
        heading = next(unit for unit in incoming["units"] if unit["text"].startswith("1. "))
        duplicate = {**heading, "anchor": "word/document.xml:p999"}
        ambiguous = {**incoming, "units": incoming["units"] + [duplicate]}

        result = self.service.compare(ambiguous, candidate["reference_id"], self.confirmation(candidate))

        self.assertEqual(result["comparison"]["status"], "limited")
        self.assertEqual([item["difference_type"] for item in result["comparison"]["observations"]], ["structural_ambiguity"])
        self.assertIn(duplicate["anchor"], {
            passage["anchor"]
            for passage in result["comparison"]["observations"][0]["incoming_passages"]
        })


if __name__ == "__main__":
    unittest.main()
