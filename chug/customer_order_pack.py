"""Conservative, source-linked comparison for the synthetic customer-order family.

This module compares an explicitly selected registry record with an extracted
document. It does not choose a baseline, interpret legal effect, or record a
human decision. The registry candidate must be selected and confirmed by the
caller before a comparison is treated as meaningful.
"""
from __future__ import annotations

import re

from .engine import ROUTE_ORDER
from .reference_registry import extract_context


_NUMBERED = re.compile(r"^(\d+)\.\s+(.+)$")
_SUPPLEMENT = re.compile(r"^(?:schedule|appendix|annex)\b.*$", re.IGNORECASE)


def _normal(text: str) -> str:
    return " ".join(text.split())


def _sections(document: dict) -> tuple[list[dict], list[dict]]:
    """Group every extracted unit without dropping preambles or non-body parts."""
    sections: list[dict] = []
    preamble: list[dict] = []
    current = None
    duplicates = []
    seen = set()

    def add(key, title, units):
        nonlocal current
        section = {"key": key, "title": title, "units": units, "number": ""}
        if units and units[0]["part"] == "word/document.xml":
            match = _NUMBERED.match(units[0]["text"])
            if match:
                section["number"] = match.group(1)
        if key in seen:
            duplicates.extend(units[:1])
            previous = next(item for item in sections if item["key"] == key)
            duplicates.extend(previous["units"][:1])
            previous["units"].extend(units)
            current = previous
        else:
            seen.add(key)
            sections.append(section)
        current = sections[-1]

    for unit in document.get("units", []):
        part = unit["part"]
        if part != "word/document.xml":
            key = "part:" + part
            if key not in seen:
                add(key, part, [unit])
            else:
                next(item for item in sections if item["key"] == key)["units"].append(unit)
            current = None
            continue

        match = _NUMBERED.match(unit["text"])
        if match:
            if preamble:
                add("preamble", "Unsectioned document text", preamble)
                preamble = []
            title = _normal(match.group(2)).casefold()
            add("clause:" + title, match.group(2), [unit])
        elif _SUPPLEMENT.match(unit["text"]):
            if preamble:
                add("preamble", "Unsectioned document text", preamble)
                preamble = []
            key = "supplement:" + _normal(unit["text"]).casefold()
            add(key, unit["text"], [unit])
        elif current is None:
            preamble.append(unit)
        else:
            current["units"].append(unit)

    if preamble:
        add("preamble", "Unsectioned document text", preamble)
    return sections, duplicates


def _evidence(units: list[dict]) -> list[dict]:
    return [{"anchor": unit["anchor"], "text": unit["text"]} for unit in units]


def _finding(category: str, title: str, explanation: str, incoming: list[dict], reference: list[dict], uncertainty: str) -> dict:
    return {
        "id": category + ":" + (incoming[0]["anchor"] if incoming else reference[0]["anchor"]),
        "category": category,
        "route": "review_required",
        "title": title,
        "explanation": explanation,
        "sources": _evidence(incoming),
        "reference": _evidence(reference),
        "uncertainty": uncertainty,
        "method": "deterministic section and text comparison",
    }


class CustomerOrderPack:
    """Compare orders only after a specific registry reference is selected."""

    id = "customer_order"
    title = "Customer order"
    route_order = ROUTE_ORDER

    def compare(self, reference_record: dict, incoming: dict) -> dict:
        reference = reference_record.get("document", {})
        identity = {
            "reference_id": reference_record.get("reference_id"),
            "version": reference_record.get("version"),
            "sha256": reference_record.get("sha256"),
            "demo_status": reference_record.get("demo_status"),
        }
        base = {
            "pack": self.id,
            "baseline": identity,
            "findings": [],
            "human_decision_required": True,
            "approved": False,
            "checks": {"extraction": "not run", "comparison": "not run"},
        }
        if reference_record.get("family") != "customer_order":
            return {**base, "route": "blocked_extraction", "status": "blocked", "reason": "Selected registry record is not a customer-order reference."}
        if (reference.get("coverage", {}).get("status") != "complete"
                or incoming.get("coverage", {}).get("status") != "complete"):
            return {**base, "route": "blocked_extraction", "status": "blocked", "reason": "Reference or incoming document extraction is incomplete; comparison did not run."}
        if not identity["sha256"] or reference.get("sha256") != identity["sha256"]:
            return {**base, "route": "blocked_extraction", "status": "blocked", "reason": "Selected reference identity does not match its extracted source."}

        context = extract_context(incoming)
        family = context.get("dimensions", {}).get("family", {})
        if context.get("status") == "ambiguous" or family.get("state") != "known" or family.get("value") != "customer_order":
            return {
                **base,
                "route": "review_required",
                "status": "needs_context",
                "reason": "Incoming agreement family is missing, ambiguous or not a customer order; section comparison did not run.",
                "context": context,
            }

        baseline, repeated_baseline = _sections(reference)
        current, repeated_current = _sections(incoming)
        findings = []
        uncertainty = "Textual comparison does not establish legal or commercial effect. A person must review the complete source and context."

        if repeated_baseline or repeated_current:
            findings.append(_finding(
                "structural_ambiguity",
                "Repeated section heading",
                "A heading occurs more than once, so section alignment is ambiguous. Inspect both documents in full.",
                repeated_current,
                repeated_baseline,
                "Repeated headings may refer to different provisions; no unique clause pairing was inferred.",
            ))
            return {
                **base,
                "route": "review_required",
                "status": "limited",
                "reason": findings[0]["title"],
                "findings": findings,
                "checks": {"extraction": "complete", "comparison": "limited"},
                "context": context,
                "assurance": {
                    "reference_sha256": identity["sha256"], "incoming_sha256": incoming.get("sha256"),
                    "reference_bytes": reference.get("size"), "incoming_bytes": incoming.get("size"),
                    "reference_passages": len(reference.get("units", [])), "incoming_passages": len(incoming.get("units", [])),
                    "limitations": [
                        "Repeated headings make section alignment ambiguous; section comparison was withheld.",
                        "Reference applicability is not established by this comparator; a human must confirm the selected baseline.",
                    ],
                },
            }

        before_by_key = {item["key"]: item for item in baseline}
        after_by_key = {item["key"]: item for item in current}
        for key, before in before_by_key.items():
            after = after_by_key.get(key)
            if after is None:
                findings.append(_finding(
                    "missing_section",
                    "Missing section: " + before["title"],
                    "This reference section has no matching heading in the incoming document. Text may have moved elsewhere; inspect the complete document before concluding it is absent.",
                    [], before["units"],
                    "A missing heading does not prove that equivalent wording is absent elsewhere.",
                ))
                continue
            old_text = _normal("\n".join(unit["text"] for unit in before["units"]))
            new_text = _normal("\n".join(unit["text"] for unit in after["units"]))
            if old_text != new_text or before["number"] != after["number"]:
                findings.append(_finding(
                    "changed_section",
                    "Changed section: " + before["title"],
                    "Section wording or numbering differs from the selected reference. Review the source passages side by side; meaning is not inferred.",
                    after["units"], before["units"], uncertainty,
                ))
        for key, after in after_by_key.items():
            if key not in before_by_key:
                findings.append(_finding(
                    "added_section",
                    "Added section: " + after["title"],
                    "This section does not appear in the selected reference. Review it and any linked or overriding provisions.",
                    after["units"], [], uncertainty,
                ))

        before_order = [item["key"] for item in baseline]
        after_order = [item["key"] for item in current]
        common_before = [key for key in before_order if key in after_by_key]
        common_after = [key for key in after_order if key in before_by_key]
        if common_before != common_after:
            headings_before = [item["units"][0] for item in baseline if item["key"] in set(common_before)]
            headings_after = [item["units"][0] for item in current if item["key"] in set(common_after)]
            findings.append(_finding(
                "section_order_change",
                "Section order differs",
                "The order of shared sections differs from the selected reference. Check cross-references and precedence language in the complete documents.",
                headings_after, headings_before,
                "Order alone does not establish an override or legal effect.",
            ))

        unapproved = reference_record.get("approval_status") != "approved"
        route = "review_required" if findings or unapproved else "routine_candidate"
        reason = (findings[0]["title"] if findings else
                  "Selected research reference is not approved; human validation is required." if unapproved else
                  "No textual section difference found within this comparison; confirm the parties and transaction.")
        limitations = ["Comparison is limited to extracted text grouped by numbered sections and named schedules/appendices.",
                       "Structured commercial fields such as quantities, fees, dates and renewal terms are surfaced as textual differences and are not interpreted.",
                       "Reference applicability is not established by this comparator; a human must confirm the selected baseline."]
        return {
            **base,
            "route": route,
            "status": "complete",
            "reason": reason,
            "findings": findings,
            "checks": {"extraction": "complete", "comparison": "complete"},
            "context": context,
            "assurance": {"reference_sha256": identity["sha256"], "incoming_sha256": incoming.get("sha256"),
                          "reference_bytes": reference.get("size"), "incoming_bytes": incoming.get("size"),
                          "reference_passages": len(reference.get("units", [])), "incoming_passages": len(incoming.get("units", [])),
                          "limitations": limitations},
        }
