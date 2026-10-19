"""Populate an isolated local Chug workspace with five fictional review cases (including an abstention).

Run from the repository root:
    python3 scripts/seed_synthetic_starter.py --state-dir /tmp/chug-starter

This is a controlled synthetic demo setup, never an import of real client files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chug.server import App

LIBRARY = ROOT / "research/reference-library-v0.1"
STARTER = (
    (
        "references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx",
        "incoming-tests/Incoming - Evaluation NDA with Longer Retention.docx",
    ),
    (
        "references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx",
        "incoming-tests/Incoming - Desktop Reseller Seat Increase.docx",
    ),
)


def seed(state_dir: Path) -> list[dict]:
    app = App(ROOT, state_dir)
    results = []
    for reference_name, changed_name in STARTER:
        reference_path = LIBRARY / reference_name
        changed_path = LIBRARY / changed_name
        reference = app.upload_reference(reference_path.read_bytes(), reference_path.name)["library_item"]
        for source, label in ((reference_path, "exact copy"), (changed_path, "changed wording")):
            # No reference ID is passed to intake: exercise automatic selection.
            detail = app.intake(source.read_bytes(), ("Incoming exact copy - " if label == "exact copy" else "") + source.name)
            results.append({
                "example": label,
                "incoming": detail["incoming"]["filename"],
                "incoming_sha256": detail["incoming"]["sha256"],
                "family": detail["family"],
                "selected_reference_id": detail["reference"]["reference_id"],
                "selected_reference_sha256": detail["reference"]["sha256"],
                "expected_reference_id": reference["reference_id"],
                "matching_status": detail["matching"]["proposal"]["status"],
                "comparison_status": detail["comparison"]["status"],
                "differences": len(detail["comparison"].get("findings", detail["comparison"].get("observations", []))),
                "human_decision": detail["human_decision"]["status"],
            })
    # The fifth case proves that a plausible but inapplicable contract is not
    # silently forced onto either Active reference. It is a real queued intake.
    ambiguous = LIBRARY / "incoming-tests/Incoming - Ambiguous Reseller Cloud Scan Purchase.docx"
    detail = app.intake(ambiguous.read_bytes(), ambiguous.name)
    results.append({
        "example": "ambiguous purchase",
        "incoming": detail["incoming"]["filename"],
        "incoming_sha256": detail["incoming"]["sha256"],
        "family": detail["family"],
        "selected_reference_id": detail["reference"]["reference_id"],
        "selected_reference_sha256": detail["reference"]["sha256"],
        "expected_reference_id": None,
        "matching_status": detail["matching"]["proposal"]["status"],
        "comparison_status": detail["comparison"]["status"],
        "differences": len(detail["comparison"].get("findings", detail["comparison"].get("observations", []))),
        "human_decision": detail["human_decision"]["status"],
        "reason": detail["reason"],
    })
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True, help="Dedicated local synthetic state directory")
    args = parser.parse_args()
    for row in seed(args.state_dir):
        print(f"{row['family']} | {row['example']} | {row['matching_status']} | {row['comparison_status']} | {row['differences']} differences | review {row['human_decision']}")
