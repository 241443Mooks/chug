"""The active mutual-NDA contract family.

This is one explicit boundary, not a registry of hypothetical products. Source
identity, persistence and the human decision ledger remain application concerns.
"""
from __future__ import annotations

import re

from .engine import ROUTE_ORDER, _tokens, analyse, clauses, duplicate_headings, load_library


class NDAPack:
    id = "mutual_nda"
    title = "Mutual NDA"
    route_order = ROUTE_ORDER

    def load_library(self, root):
        return load_library(root)

    def reference_path(self, root):
        return next((root / "dataset/reference").glob("*.docx"))

    def incoming_path(self, root, document_id):
        return next((root / "dataset/incoming").glob(document_id + "-*.docx"))

    def historical_path(self, root, document_id):
        return next((root / "dataset/historical").glob(document_id + "-*.docx"), None)

    def validate_reference(self, document, bundled_reference):
        if document["coverage"]["status"] != "complete" or duplicate_headings(document):
            raise ValueError("Reference extraction or clause alignment is incomplete; choose a supported synthetic NDA")
        if not set(clauses(bundled_reference)).issubset(clauses(document)):
            raise ValueError("Reference has different or missing clause headings; this prototype needs the bundled NDA clause family")

    def analyse(self, reference, document, historical, decisions, published, bundled_reference):
        known = reference["sha256"] == bundled_reference["sha256"]
        report = analyse(reference, document, historical if known else {}, decisions if known else {}, published)
        if not known:
            report["assurance"]["limitations"].append("Uploaded reference has not been approved as organisational guidance; compare its provisions and context before deciding.")
            if report["route"] == "routine_candidate":
                report["route"] = "review_required"
                report["reason"] = "Uploaded reference requires human validation before a routine route"
        report["history_scope"] = {"historical_records": len(historical) if known else 0, "active_published_records": len(published), "shown": len(report["precedents"]), "method": "lexical ranking of changed passages and clause topics"}
        return report

    def blocked_analysis(self, reference, document):
        return analyse(reference, document, {}, {})

    def section_title(self, document, source_anchor):
        return next((section["title"] for section in clauses(document).values() if any(unit["anchor"] == source_anchor for unit in section["units"])), "")

    def shared_terms(self, previous_text, current_text):
        return sorted(_tokens(previous_text) & _tokens(current_text))

    def display_name(self, document):
        for unit in document["units"]:
            if unit["part"] == "word/document.xml":
                match = re.search(r"made between (.+?) and (.+?)\. The parties wish", unit["text"])
                if match:
                    parties = [match.group(1), match.group(2)]
                    other = next((party for party in parties if party != "Northbridge Systems Ltd"), parties[0])
                    return other + " · Mutual NDA"
        return document["filename"].removesuffix(".docx")
