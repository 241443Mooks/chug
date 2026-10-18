"""Synthetic applicability matching tests; never use expected-match answer keys."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from chug.reference_registry import load_registry, propose_reference

ROOT = Path(__file__).resolve().parents[1]


def document(*paragraphs):
    return {
        "filename": "synthetic-input.docx",
        "coverage": {"status": "complete"},
        "units": [
            {"anchor": "word/document.xml:p" + str(index), "text": text}
            for index, text in enumerate(paragraphs, 1)
        ],
    }


class ReferenceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.references = load_registry(ROOT)

    def test_eight_sources_are_hashed_complete_and_unapproved(self):
        self.assertEqual(len(self.references), 8)
        for reference in self.references:
            self.assertEqual(reference["document"]["coverage"]["status"], "complete")
            self.assertEqual(reference["sha256"], reference["document"]["sha256"])
            self.assertEqual(reference["demo_status"], "fictional_research_candidate_not_approved")
            self.assertEqual(reference["approval_status"], "unapproved_demo_candidate")

    def test_mutual_evaluation_proposal_points_to_observed_incoming_evidence(self):
        incoming = document(
            "Mutual NDA — Product evaluation (UK)",
            "Purpose: evaluate a possible software purchase and technical integration.",
            "England and Wales. Both parties may exchange confidential information.",
        )
        result = propose_reference(incoming, self.references)
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["proposal"]["reference_id"], "NDA-UK-EVAL")
        self.assertEqual(result["proposal"]["demo_status"], "fictional_research_candidate_not_approved")
        reasons = result["proposal"]["reasons"]
        self.assertTrue(any(row["dimension"] == "variant" and any(evidence["anchor"] == "word/document.xml:p2" for evidence in row["evidence"]) for row in reasons))
        self.assertTrue(result["human_confirmation_required"])
        self.assertFalse(result["comparison_allowed"])

    def test_supplier_and_one_way_contexts_exclude_other_nda_variants(self):
        supplier = propose_reference(document(
            "Mutual NDA — Supplier assessment (UK)",
            "Purpose: supplier due diligence and procurement discussions.",
            "England and Wales. Both parties may share confidential information.",
        ), self.references)
        self.assertEqual(supplier["proposal"]["reference_id"], "NDA-UK-SUPPLIER")
        self.assertIn("NDA-UK-EVAL", {row["reference_id"] for row in supplier["excluded"]})

        one_way = propose_reference(document(
            "One-way Non-Disclosure Agreement — UK",
            "Purpose: disclose product details to a potential customer.",
            "England and Wales. Northbridge is the Disclosing Party; Sample Customer is the Receiving Party.",
        ), self.references)
        self.assertEqual(one_way["proposal"]["reference_id"], "NDA-UK-ONEWAY")

        one_way_supplier = propose_reference(document(
            "One-way NDA — supplier assessment",
            "Purpose: supplier due diligence for a security assessment.",
            "England and Wales. Northbridge is the Disclosing Party; the supplier is the Receiving Party.",
        ), self.references)
        self.assertIsNone(one_way_supplier["proposal"])
        self.assertEqual(one_way_supplier["status"], "no_suitable_match")

    def test_cloud_order_candidate_is_proposed_with_its_unstated_jurisdiction_gap(self):
        result = propose_reference(document(
            "Customer Order — Managed cloud scanning",
            "Channel: direct order from the supplier.",
            "Deployment: vendor-hosted managed cloud scanning for authorised web application testing.",
        ), self.references)
        self.assertEqual(result["status"], "proposed_with_gaps")
        self.assertEqual(result["proposal"]["reference_id"], "ORDER-DAST-CLOUD")
        self.assertTrue(any("jurisdiction" in gap for gap in result["proposal"]["gaps"]))
        self.assertTrue(result["questions"])

    def test_reseller_hosted_cloud_has_no_candidate_and_never_falls_back_to_direct(self):
        result = propose_reference(document(
            "Customer Order — reseller hosted cloud scanning",
            "Purchase by an authorised reseller for a named end customer.",
            "Deployment: vendor-hosted managed cloud scanning.",
        ), self.references)
        self.assertIsNone(result["proposal"])
        self.assertEqual(result["status"], "no_suitable_match")
        self.assertEqual(len(result["excluded"]), 8)

    def test_scope_ranking_breaks_a_tie_only_when_evidence_is_distinct(self):
        alternate = dict(self.references[0])
        alternate["reference_id"] = "NDA-UK-EVAL-ALT"
        alternate["display_name"] = "Mutual NDA — Alternate product evaluation (UK)"
        alternate["scope"] = "Mutual NDA — Product evaluation (UK)"
        alternate["scope_anchor"] = "word/document.xml:p1"
        # Keep only the incoming title's scope terms so the source-linked title
        # scope outranks the unrelated full-purpose paragraph by observable overlap.
        short_incoming = document(
            "Mutual NDA — Product evaluation (UK)",
            "England and Wales. Both parties may exchange confidential information.",
        )
        ranked = propose_reference(short_incoming, [self.references[0], alternate])
        self.assertEqual(ranked["proposal"]["reference_id"], "NDA-UK-EVAL-ALT")
        self.assertEqual(ranked["alternatives"][0]["reference_id"], "NDA-UK-EVAL")
        self.assertTrue(ranked["proposal"]["ranking"]["shared_terms"])

        tied = propose_reference(short_incoming, [self.references[0], dict(self.references[0], reference_id="NDA-UK-EVAL-SECOND")])
        self.assertEqual(tied["status"], "ambiguous_match")
        self.assertIsNone(tied["proposal"])

    def test_missing_or_conflicting_context_abstains(self):
        missing_channel = propose_reference(document(
            "Customer Order — Managed cloud scanning",
            "Deployment: vendor-hosted managed cloud scanning.",
        ), self.references)
        self.assertIsNone(missing_channel["proposal"])
        self.assertEqual(missing_channel["status"], "needs_context")
        self.assertTrue(any("direct or through a reseller" in question for question in missing_channel["questions"]))

        conflict = propose_reference(document(
            "Customer Order — Managed cloud scanning",
            "This direct order is placed through an authorised reseller.",
            "Deployment: vendor-hosted managed cloud scanning.",
        ), self.references)
        self.assertIsNone(conflict["proposal"])
        self.assertEqual(conflict["status"], "ambiguous_context")

    def test_incomplete_extraction_blocks_matching(self):
        incoming = document("Mutual NDA — Product evaluation (UK)")
        incoming["coverage"]["status"] = "blocked"
        result = propose_reference(incoming, self.references)
        self.assertEqual(result["status"], "blocked_extraction")
        self.assertIsNone(result["proposal"])

    def test_loader_does_not_open_evaluation_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "research/reference-library-v0.1"
            shutil.copytree(ROOT / "research/reference-library-v0.1/references", destination / "references")
            catalog = json.loads((ROOT / "research/reference-library-v0.1/catalog.json").read_text())
            self.assertNotIn("incoming_tests", catalog)
            (destination / "catalog.json").write_text(json.dumps(catalog))
            evaluation = destination / "evaluation-only"
            evaluation.mkdir()
            (evaluation / "expected-matches.json").write_text("not runtime-readable JSON")
            self.assertEqual(len(load_registry(Path(temporary))), 8)

    def test_catalog_rejects_embedded_evaluation_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "research/reference-library-v0.1"
            shutil.copytree(ROOT / "research/reference-library-v0.1/references", destination / "references")
            catalog = json.loads((ROOT / "research/reference-library-v0.1/catalog.json").read_text())
            catalog["incoming_tests"] = [{"expected_candidate_reference_id": "must-not-load"}]
            (destination / "catalog.json").write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, "reference records only"):
                load_registry(Path(temporary))


if __name__ == "__main__":
    unittest.main()
