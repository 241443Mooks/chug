"""Verified, synthetic reference registry and conservative context matcher.

This module reads only the reference records and their named source documents.
Evaluation fixtures and expected matches are deliberately outside its input path.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .document import extract_file


LIBRARY = Path("research/reference-library-v0.1")
REQUIRED_FIELDS = {
    "reference_id", "display_name", "family", "variant", "deployment", "channel",
    "direction", "jurisdiction", "scope", "scope_anchor", "file", "sha256",
    "approval_status", "version", "demo_status",
}
DEMO_STATUS = "fictional_research_candidate_not_approved"


def load_registry(root: Path) -> list[dict]:
    """Load and verify each reference; do not enumerate or open evaluation inputs."""
    library = (root / LIBRARY).resolve()
    catalog_path = library / "catalog.json"
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "incoming_tests" in payload or "expected_matches" in payload:
        raise ValueError("Reference catalogue must contain reference records only")
    records = payload.get("references")
    if not isinstance(records, list) or not records:
        raise ValueError("Reference catalogue has no reference records")

    result = []
    seen = set()
    for source in records:
        if not isinstance(source, dict) or not REQUIRED_FIELDS.issubset(source):
            raise ValueError("Reference catalogue record is incomplete")
        reference_id = source["reference_id"]
        if not isinstance(reference_id, str) or not reference_id or reference_id in seen:
            raise ValueError("Reference IDs must be unique non-empty strings")
        seen.add(reference_id)
        if source["demo_status"] != DEMO_STATUS or source["approval_status"] != "unapproved_demo_candidate":
            raise ValueError("Research references must remain visibly unapproved demo candidates")
        if not isinstance(source["family"], str) or source["family"] not in {"nda", "customer_order"} or not isinstance(source["variant"], str) or not source["variant"]:
            raise ValueError("Reference family and variant are invalid")
        for field in ("display_name", "file", "scope", "scope_anchor", "version"):
            if not isinstance(source[field], str) or not source[field].strip():
                raise ValueError("Reference field must be a non-empty string: " + field)
        for field in ("deployment", "channel", "direction", "jurisdiction"):
            if source[field] is not None and (not isinstance(source[field], str) or not source[field].strip()):
                raise ValueError("Reference field must be a string or null: " + field)
        if not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
            raise ValueError("Reference source hash is invalid")
        relative = Path(source["file"])
        if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "references":
            raise ValueError("Reference source must be inside the controlled references directory")
        source_path = (library / relative).resolve()
        if not source_path.is_relative_to(library / "references"):
            raise ValueError("Reference source escapes the controlled references directory")
        if not source_path.is_file():
            raise ValueError("Reference source is missing: " + reference_id)
        document = extract_file(source_path)
        if document["coverage"]["status"] != "complete":
            raise ValueError("Reference source extraction is incomplete: " + reference_id)
        if document["sha256"] != source["sha256"]:
            raise ValueError("Reference source hash changed: " + reference_id)
        scope_anchor = source["scope_anchor"]
        scope_unit = next((unit for unit in document["units"] if unit["anchor"] == scope_anchor), None)
        if not scope_unit or source["scope"] not in scope_unit["text"]:
            raise ValueError("Reference scope metadata has no matching source passage: " + reference_id)
        result.append({**source, "document": document, "source_path": source_path})
    return result


def _evidence(unit: dict, reason: str) -> dict:
    return {"anchor": unit["anchor"], "text": unit["text"], "reason": reason}


def _dimension(value=None, evidence=(), state="known"):
    return {"state": state, "value": value, "evidence": list(evidence)}


def _matches(units, pattern, reason):
    regex = re.compile(pattern, re.IGNORECASE)
    return [_evidence(unit, reason) for unit in units if regex.search(unit["text"])]


def _resolve(values):
    """Return one value, unknown, or ambiguous; never choose between conflicts."""
    found = {}
    for value, evidence in values:
        if value is not None and evidence:
            found.setdefault(value, []).extend(evidence)
    if not found:
        return _dimension(None, (), "unknown")
    if len(found) > 1:
        evidence = [item for group in found.values() for item in group]
        return _dimension(None, evidence, "ambiguous")
    value, evidence = next(iter(found.items()))
    return _dimension(value, evidence)


_RANK_STOP = {"a", "an", "and", "for", "in", "of", "or", "the", "to", "with", "by", "as", "from"}


def _rank_by_scope(item, incoming_text):
    scope_tokens = {token for token in re.findall(r"[a-z0-9]+", (item["reference"].get("scope") or "").casefold()) if token not in _RANK_STOP}
    input_tokens = {token for token in re.findall(r"[a-z0-9]+", incoming_text.casefold()) if token not in _RANK_STOP}
    shared = sorted(scope_tokens & input_tokens)
    item["ranking"] = {"basis": "shared scope words after hard applicability exclusions", "shared_terms": shared, "score": len(shared)}
    return item


def extract_context(document: dict) -> dict:
    """Extract applicability facts with exact source anchors from a supported source."""
    if document.get("coverage", {}).get("status") != "complete":
        return {"status": "blocked_extraction", "dimensions": {}}
    units = document.get("units", [])
    family_hits = []
    nda = _matches(units, r"\b(?:mutual\s+)?NDA\b|\bnon[- ]disclosure agreement\b", "NDA wording")
    order = _matches(units, r"\bcustomer order\b|\border form\b", "customer order wording")
    if nda:
        family_hits.append(("nda", nda))
    if order:
        family_hits.append(("customer_order", order))
    family = _resolve(family_hits)

    direction = _dimension(None, (), "unknown")
    variant = _dimension(None, (), "unknown")
    purpose = _dimension(None, (), "unknown")
    deployment = _dimension(None, (), "unknown")
    channel = _dimension(None, (), "unknown")
    jurisdiction = _dimension(None, (), "unknown")

    if family["state"] == "known" and family["value"] == "nda":
        mutual = _matches(units, r"\bmutual\s+NDA\b|\bboth parties may (?:share|exchange|disclose)\b|\bthe parties may (?:share|exchange|disclose)\b|\beach party may (?:share|exchange|disclose)\b", "mutual disclosure wording")
        one_way = _matches(units, r"\bone[- ]way NDA\b|\bDisclosing Party\b|\bReceiving Party\b", "one-way disclosure role wording")
        direction = _resolve([("mutual", mutual), ("one_way", one_way)])
        evaluation = _matches(units, r"\b(?:product evaluation|evaluate? a possible software|software purchase|technical integration)\b", "product evaluation or prospective-customer purpose")
        supplier = _matches(units, r"\b(?:supplier (?:due diligence|assessment)|procurement|security assessment|potential supplier|service provider)\b", "supplier assessment or procurement purpose")
        customer_disclosure = _matches(units, r"\b(?:potential customer|customer disclosure|commercial relationship)\b", "prospective-customer disclosure purpose")
        purpose = _resolve([("product_evaluation", evaluation), ("supplier_assessment", supplier), ("customer_disclosure", customer_disclosure)])
        if direction["state"] == "known" and purpose["state"] == "known":
            variant_map = {
                ("mutual", "product_evaluation"): "mutual_evaluation",
                ("mutual", "supplier_assessment"): "mutual_supplier_due_diligence",
                ("one_way", "customer_disclosure"): "one_way_customer_disclosure",
            }
            variant_name = variant_map.get((direction["value"], purpose["value"]), "unsupported_scope")
            variant = _dimension(variant_name, direction["evidence"] + purpose["evidence"])
    elif family["state"] == "known" and family["value"] == "customer_order":
        direct = _matches(units, r"\bdirect\b|\bdirectly\b", "explicit direct sales channel")
        reseller = _matches(units, r"\breseller\b|\bresale\b|\bthrough an? (?:authorised|authorized) reseller\b", "reseller channel wording")
        channel = _resolve([("direct", direct), ("reseller", reseller)])

        hosted_cloud = _matches(units, r"\b(?:vendor[- ]hosted|managed cloud scanning|cloud scanning|DAST cloud|hosted scanning)\b", "vendor-hosted cloud service wording")
        self_hosted = _matches(units, r"\b(?:self[- ]hosted|customer[- ]hosted|customer operates the instance)\b", "customer-hosted deployment wording")
        desktop = _matches(units, r"\b(?:desktop user licen[cs]es?|named desktop (?:software )?users?|desktop seats?)\b", "desktop licence scope")
        mixed = _matches(units, r"\b(?:combined order|desktop plus cloud|desktop and cloud bundle)\b", "combined desktop and cloud scope")
        deployment_values = []
        if mixed:
            deployment_values.append(("mixed", mixed))
        else:
            if hosted_cloud:
                deployment_values.append(("vendor_cloud", hosted_cloud))
            if self_hosted:
                deployment_values.append(("customer_hosted", self_hosted))
            if desktop:
                deployment_values.append(("desktop", desktop))
        if hosted_cloud and desktop:
            deployment_values = [("mixed", hosted_cloud + desktop)]
        deployment = _resolve(deployment_values)
        if deployment["state"] == "known" and channel["state"] == "known":
            order_variants = {
                ("desktop", "direct"): "desktop_seats",
                ("vendor_cloud", "direct"): "managed_cloud_scanning",
                ("customer_hosted", "direct"): "self_hosted_scanning",
                ("mixed", "direct"): "combined_bundle",
                ("desktop", "reseller"): "desktop_reseller",
            }
            variant_name = order_variants.get((deployment["value"], channel["value"]), "unsupported_scope")
            variant = _dimension(variant_name, deployment["evidence"] + channel["evidence"])

    uk = _matches(units, r"\bEngland and Wales\b", "explicit England and Wales jurisdiction wording")
    other_jurisdiction = _matches(units, r"\bgoverned by the laws? of ([A-Z][A-Za-z ]+)\b", "express governing-law wording")
    other_values = []
    for evidence in other_jurisdiction:
        match = re.search(r"governed by the laws? of ([A-Z][A-Za-z ]+)", evidence["text"])
        if match:
            other_values.append((match.group(1).strip(), [evidence]))
    jurisdiction = _resolve([("England and Wales", uk), *other_values])

    dimensions = {"family": family, "direction": direction, "purpose": purpose, "deployment": deployment, "channel": channel, "jurisdiction": jurisdiction, "variant": variant}
    ambiguous = [name for name, item in dimensions.items() if item["state"] == "ambiguous"]
    return {"status": "ambiguous" if ambiguous else "complete", "ambiguous_dimensions": ambiguous, "dimensions": dimensions}


def uploaded_reference_metadata(document: dict, display_name: str, version: str = "1.0") -> dict:
    """Build immutable, source-linked metadata for a locally uploaded standard.

    Applicability facts are extracted from the source. Missing facts remain
    explicit unknowns. The local legal-team upload flow is the fictional
    authorisation boundary for this synthetic prototype.
    """
    context = extract_context(document)
    dimensions = context.get("dimensions", {})
    family_dimension = dimensions.get("family", {})
    if document.get("coverage", {}).get("status") != "complete":
        raise ValueError("Reference extraction is incomplete: " + "; ".join(document.get("coverage", {}).get("issues", [])))
    if family_dimension.get("state") != "known":
        raise ValueError("Could not determine one supported reference family from the extracted source")
    family = family_dimension["value"]
    if family not in {"nda", "customer_order"}:
        raise ValueError("Only synthetic NDA and customer-order references are supported")

    def fact(name):
        item = dimensions.get(name, {})
        return item.get("value") if item.get("state") == "known" else None

    if not isinstance(display_name, str) or not display_name.strip() or len(display_name.strip()) > 120:
        raise ValueError("Reference display name must be 1 to 120 characters")
    if not isinstance(version, str) or not version.strip() or len(version.strip()) > 40:
        raise ValueError("Reference version must be 1 to 40 characters")
    variant_evidence = dimensions.get("variant", {}).get("evidence", [])
    scope_evidence = variant_evidence or family_dimension.get("evidence", [])
    scope_anchor = scope_evidence[0]["anchor"] if scope_evidence else None
    units_by_anchor = {unit["anchor"]: unit for unit in document.get("units", [])}
    scope = units_by_anchor.get(scope_anchor, {}).get("text")
    return {
        "reference_id": "UP-" + document["sha256"],
        "display_name": display_name.strip(),
        "family": family,
        "variant": fact("variant"),
        "deployment": fact("deployment"),
        "channel": fact("channel"),
        "direction": fact("direction"),
        "purpose": fact("purpose"),
        "jurisdiction": fact("jurisdiction"),
        "scope": scope,
        "scope_anchor": scope_anchor,
        "applicability": {name: {"state": item.get("state", "unknown"), "value": item.get("value"), "evidence": item.get("evidence", [])} for name, item in dimensions.items()},
        "original_filename": document["filename"],
        "sha256": document["sha256"],
        "version": version.strip(),
        "status": "active",
        "provenance": "locally_uploaded_synthetic_reference",
        "extraction": {"status": document["coverage"]["status"], "limitations": [*document["coverage"].get("issues", []), *document["coverage"].get("limitations", [])], "passage_count": len(document.get("units", [])), "parts": list(document["coverage"].get("parts", []))},
    }


def propose_reference(document: dict, references: list[dict], eligible_statuses: set[str] | None = None) -> dict:
    """Propose an exact-context candidate or abstain; never approve a baseline."""
    context = extract_context(document)
    inactive = []
    eligible_references = []
    for reference in references:
        status = reference.get("status")
        if status in {"superseded", "withdrawn"}:
            inactive.append({"reference_id": reference.get("reference_id"), "display_name": reference.get("display_name"), "status": status, "reasons": ["inactive standards are excluded from new matches"]})
        elif eligible_statuses is not None and status not in eligible_statuses:
            reason = "legacy NDA comparison baseline is retained for the existing NDA flow and has no confirmed applicability metadata for new matching" if status == "legacy_nda_baseline" else "research fixtures are not Active standards and are excluded from new matches"
            inactive.append({"reference_id": reference.get("reference_id"), "display_name": reference.get("display_name"), "status": status, "reasons": [reason]})
        else:
            eligible_references.append(reference)
    base = {"context": context, "proposal": None, "eligible": [], "excluded": inactive, "questions": [], "human_confirmation_required": True, "comparison_allowed": False}
    if context["status"] == "blocked_extraction":
        return {**base, "status": "blocked_extraction", "reason": "Document extraction is incomplete; applicability cannot be assessed."}
    if context["status"] == "ambiguous":
        return {**base, "status": "ambiguous_context", "reason": "The source contains conflicting applicability cues; resolve them before selecting a reference."}
    dims = context["dimensions"]
    family = dims["family"]
    if family["state"] != "known":
        return {**base, "status": "needs_context", "reason": "Agreement family is not explicit in the extracted source.", "questions": ["Is this an NDA or a customer order?"]}

    required = ["family", "direction", "variant"] if family["value"] == "nda" else ["family", "deployment", "channel", "variant"]
    relevant = required + ["jurisdiction"]
    missing_required = list(required)
    if family["value"] == "nda" and any(r.get("family") == "nda" and r.get("jurisdiction") for r in eligible_references):
        missing_required.append("jurisdiction")
    missing = [name for name in missing_required if dims[name]["state"] != "known"]
    if missing:
        questions = {
            "direction": "Is disclosure mutual or one-way?",
            "variant": "What transaction purpose does the agreement cover?",
            "deployment": "Is the order for desktop, vendor-hosted cloud, customer-hosted, or a combined service?",
            "channel": "Is the order direct or through a reseller?",
            "jurisdiction": "Which jurisdiction governs this transaction?",
        }
        return {**base, "status": "needs_context", "reason": "A required applicability fact is missing or ambiguous.", "questions": [questions[name] for name in missing]}

    eligible, excluded = [], list(inactive)
    for reference in eligible_references:
        reasons = []
        mismatches = []
        for name in relevant:
            incoming = dims[name]
            expected = reference.get(name)
            if name == "family" and expected is None:
                mismatches.append(name)
            elif name in required and expected is None:
                mismatches.append("reference does not establish " + name)
            elif expected is not None and incoming["state"] == "known":
                if incoming["value"] != expected:
                    mismatches.append(name)
                else:
                    reasons.append({"dimension": name, "value": expected, "evidence": incoming["evidence"]})
            elif expected is not None and name in required:
                mismatches.append(name)
        if mismatches:
            excluded.append({"reference_id": reference["reference_id"], "display_name": reference["display_name"], "reasons": ["incompatible or unresolved: " + ", ".join(mismatches)]})
            continue
        gaps = []
        for name in relevant:
            expected = reference.get(name)
            incoming = dims[name]
            if expected is None and name in {"jurisdiction", "deployment", "channel", "direction"}:
                gaps.append("Reference source does not specify " + name.replace("_", " ") + ".")
            if incoming["state"] != "known" and name == "jurisdiction":
                gaps.append("Incoming document does not establish " + name.replace("_", " ") + ".")
        eligible.append(_rank_by_scope({"reference": reference, "reasons": reasons, "gaps": gaps}, "\n".join(unit["text"] for unit in document.get("units", []))))

    if not eligible:
        return {**base, "status": "no_suitable_match", "reason": "No reference matches the extracted family and applicability context.", "excluded": excluded}
    eligible.sort(key=lambda item: (-item["ranking"]["score"], item["reference"]["reference_id"]))
    alternatives = []
    if len(eligible) > 1:
        if eligible[0]["ranking"]["score"] == 0 or eligible[0]["ranking"]["score"] == eligible[1]["ranking"]["score"]:
            return {**base, "status": "ambiguous_match", "reason": "Multiple applicable-scope candidates remain tied; an authorised reviewer must resolve applicability.", "eligible": [_public_candidate(candidate) for candidate in eligible], "excluded": excluded}
        alternatives = [_public_candidate(candidate) for candidate in eligible[1:]]

    item = eligible[0]
    status = "proposed_with_gaps" if item["gaps"] else "proposed"
    questions = ["Confirm reference scope and any unstated applicability facts with an authorised reviewer."] if item["gaps"] else []
    return {
        **base,
        "status": status,
        "reason": "One context-compatible reference remains. Confirm its applicability before comparison.",
        "proposal": _public_candidate(item),
        "alternatives": alternatives,
        "excluded": excluded,
        "questions": questions,
    }


def _public_candidate(item):
    reference = item["reference"]
    scope_unit = next(unit for unit in reference["document"]["units"] if unit["anchor"] == reference["scope_anchor"])
    return {
        "reference_id": reference["reference_id"],
        "display_name": reference["display_name"],
        "family": reference["family"],
        "variant": reference["variant"],
        "deployment": reference["deployment"],
        "channel": reference["channel"],
        "direction": reference["direction"],
        "jurisdiction": reference["jurisdiction"],
        "scope": reference["scope"],
        "scope_evidence": {"anchor": scope_unit["anchor"], "text": scope_unit["text"]},
        "version": reference["version"],
        "sha256": reference["sha256"],
        "status": reference.get("status", "research_candidate" if reference.get("demo_status") else "active"),
        "demo_status": reference.get("demo_status"),
        "reasons": item["reasons"],
        "ranking": item["ranking"],
        "gaps": item["gaps"],
    }
