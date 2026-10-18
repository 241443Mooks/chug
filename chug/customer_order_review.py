"""Application boundary for reviewer-led customer-order comparison.

Candidate matching, explicit baseline confirmation, textual observations,
routing, and a legal review decision are represented as separate states. This
module does not persist decisions or alter the existing NDA review pathway.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .customer_order_pack import CustomerOrderPack
from .reference_registry import load_registry, propose_reference


class CustomerOrderReview:
    """Orchestrate reference proposal and comparison for one extracted order."""

    def __init__(self, root: Path):
        self.references = load_registry(root)
        self.order_references = {
            item["reference_id"]: item
            for item in self.references
            if item.get("family") == "customer_order"
        }
        self.comparator = CustomerOrderPack()

    def prepare(self, incoming: dict[str, Any]) -> dict[str, Any]:
        """Return applicability context and eligible reference proposals."""
        result = propose_reference(incoming, self.references)
        candidates = []
        if result.get("proposal"):
            candidates.append(result["proposal"])
            candidates.extend(result.get("alternatives", []))
        candidates.extend(result.get("eligible", []))
        candidates = [item for item in candidates if item.get("family") == "customer_order"]
        proposal = next((item for item in candidates if item["reference_id"] == (result.get("proposal") or {}).get("reference_id")), None)
        proposal_status = result["status"]
        if result.get("proposal") and result["proposal"].get("family") != "customer_order":
            proposal_status = "wrong_family"
        return {
            "incoming": self._document_identity(incoming),
            "applicability": result,
            "eligible_candidates": candidates,
            "reference_proposal": {
                "status": proposal_status,
                "reference_id": proposal["reference_id"] if proposal else None,
                "human_confirmation_required": True,
                "comparison_allowed": False,
            },
            "reference_confirmation": {"status": "pending"},
            "comparison": {"status": "not_run", "observations": []},
            "routing": {"route": self._precomparison_route(result), "reason": result["reason"]},
            "human_decision": {"status": "pending", "required": True, "outcome": None},
        }

    def compare(
        self,
        incoming: dict[str, Any],
        reference_id: str,
        confirmation: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare only a currently eligible reference explicitly confirmed by a reviewer.

        ``confirmation`` must identify the same reference and immutable source
        hash and include a reviewer label. It confirms baseline applicability
        only; it is not a legal decision or approval of the order.
        """
        prepared = self.prepare(incoming)
        allowed = {item["reference_id"]: item for item in prepared["eligible_candidates"]}
        selected = self.order_references.get(reference_id)
        if selected is None:
            return self._not_compared(prepared, "reference_unavailable", "Selected reference is not in the verified customer-order registry.")
        if reference_id not in allowed:
            return self._not_compared(
                prepared,
                "reference_not_eligible",
                "Selected reference is not among the candidates supported by this order's extracted context.",
            )
        if not self._confirmation_matches(confirmation, selected):
            return self._not_compared(
                prepared,
                "confirmation_required",
                "A reviewer must explicitly confirm this reference ID and source hash before comparison.",
            )

        report = self.comparator.compare(selected, incoming)
        candidate = allowed[reference_id]
        prepared["reference_proposal"] = {
            "status": prepared["applicability"]["status"],
            "reference_id": candidate["reference_id"],
            "human_confirmation_required": True,
            "comparison_allowed": False,
        }
        prepared["reference_confirmation"] = {
            "status": "confirmed",
            "reference_id": reference_id,
            "version": selected["version"],
            "sha256": selected["sha256"],
            "reviewer": confirmation["reviewer"],
            "timestamp": confirmation.get("timestamp"),
            "rationale": confirmation.get("rationale", ""),
        }
        prepared["comparison"] = {
            "status": report["checks"]["comparison"],
            "method": "deterministic section and text comparison" if report["findings"] or report["checks"]["comparison"] == "complete" else None,
            "baseline": report["baseline"],
            "observations": [self._observation(finding) for finding in report["findings"]],
            "assurance": report.get("assurance", {}),
            "missing_information": self._missing_information(candidate, report),
        }
        prepared["routing"] = {"route": report["route"], "reason": report["reason"]}
        prepared["human_decision"] = {"status": "pending", "required": True, "outcome": None}
        prepared["comparison"]["human_decision_required"] = True
        prepared["comparison"]["approved"] = False
        return prepared

    @staticmethod
    def _confirmation_matches(confirmation: Any, selected: dict) -> bool:
        return (
            isinstance(confirmation, dict)
            and confirmation.get("confirmed") is True
            and confirmation.get("reference_id") == selected["reference_id"]
            and confirmation.get("sha256") == selected["sha256"]
            and isinstance(confirmation.get("reviewer"), str)
            and bool(confirmation["reviewer"].strip())
        )

    @staticmethod
    def _document_identity(document: dict) -> dict:
        return {"filename": document.get("filename"), "sha256": document.get("sha256")}

    @staticmethod
    def _precomparison_route(result: dict) -> str:
        if result["status"] == "blocked_extraction":
            return "blocked_extraction"
        if result["status"] in {"proposed", "proposed_with_gaps", "ambiguous_match"}:
            return "review_required"
        return "review_required"

    @staticmethod
    def _observation(finding: dict) -> dict:
        return {
            "id": finding["id"],
            "difference_type": finding["category"],
            "title": finding["title"],
            "explanation": finding["explanation"],
            "incoming_passages": finding["sources"],
            "reference_passages": finding["reference"],
            "missing_information": (
                ["Confirm whether the missing heading's protection appears elsewhere in the complete order."]
                if finding["category"] == "missing_section" else []
            ),
            "uncertainty": finding["uncertainty"],
            "method": finding["method"],
        }

    @staticmethod
    def _missing_information(candidate: dict, report: dict) -> list[str]:
        gaps = list(candidate.get("gaps", []))
        for finding in report["findings"]:
            if finding["category"] == "missing_section":
                gaps.append("Confirm whether the missing heading's protection appears elsewhere in the complete order.")
        return list(dict.fromkeys(gaps))

    @staticmethod
    def _not_compared(prepared: dict, status: str, reason: str) -> dict:
        prepared["comparison"] = {"status": "not_run", "observations": [], "reason": reason}
        prepared["routing"] = {"route": "review_required", "reason": reason, "status": status}
        return prepared
