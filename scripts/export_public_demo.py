"""Build a read-only, synthetic-only snapshot for static Chug hosting.

Run from any working directory:
    python3 scripts/export_public_demo.py

Never export local reviewer state, uploaded agreements, private data, ground truth,
or matching expectations. The public snapshot is not an interactive legal service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # Allow direct script execution from any directory.

from chug.server import App
SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_verified(source: Path, target: Path, expected_sha256: str | None = None) -> str:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("Source identity changed: " + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return digest


def export(destination: Path) -> None:
    # A new empty temporary ledger ensures no real or locally entered decisions escape.
    # Clean the entire generated subtree so withdrawn fixture files cannot linger.
    if destination.resolve() in (ROOT.resolve(), (ROOT / "web").resolve()) or not destination.resolve().is_relative_to((ROOT / "web").resolve()):
        raise ValueError("Export must stay inside web/ to prevent destructive cleanup")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="chug-public-snapshot-") as temp:
        app = App(ROOT, Path(temp))
        write_json(destination / "queue.json", {"items": app.queue()})
        write_json(destination / "reference.json", app.reference_info())

        for document_id, item in app.contracts.items():
            if not SAFE_NAME.fullmatch(document_id):
                raise ValueError("Unexpected contract ID")
            write_json(destination / "contracts" / (document_id + ".json"), app.detail(document_id))
            copy_verified(
                item["path"],
                destination / "originals" / "contracts" / (document_id + ".docx"),
                item["document"]["sha256"],
            )

        for document_id, document in app.historical.items():
            if not SAFE_NAME.fullmatch(document_id):
                raise ValueError("Unexpected historical ID")
            write_json(
                destination / "history" / (document_id + ".json"),
                {"document": document, "decision": app.decisions[document_id]},
            )
            source = app.pack.historical_path(ROOT, document_id)
            if source is None:
                raise ValueError("Missing historical original: " + document_id)
            copy_verified(source, destination / "originals" / "history" / (document_id + ".docx"), document["sha256"])

        for digest, item in app.references.items():
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Unexpected reference hash")
            copy_verified(
                item["path"],
                destination / "originals" / "references" / (digest + ".docx"),
                digest,
            )

    # Separate research catalogue: visible specimens, not active review baselines.
    # Never copy incoming_tests expected_candidate_reference_id or evaluation answers.
    library = ROOT / "research" / "reference-library-v0.1"
    records: dict[str, object] = {
        "notice": "Research-only synthetic specimens. No applicability check, legal approval, comparison, or route has been performed.",
        "references": [],
        "routine_clients": [],
        "challenge_cases": [],
    }
    catalog_path = library / "catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        for entry in catalog["references"]:
            source = (library / entry["file"]).resolve()
            if not source.is_relative_to(library.resolve()) or not source.is_file():
                raise ValueError("Invalid research reference path")
            reference_id = entry["reference_id"]
            if not SAFE_NAME.fullmatch(reference_id):
                raise ValueError("Invalid reference ID")
            target = destination / "originals" / "research" / (reference_id + ".docx")
            digest = copy_verified(source, target)
            records["references"].append({
                "id": reference_id,
                "name": entry["display_name"],
                "family": entry["family"],
                "variant": entry["variant"],
                "deployment": entry.get("deployment"),
                "channel": entry.get("channel"),
                "version": entry["version"],
                "approval_status": "unapproved_demo_candidate",
                "sha256": digest,
                "download": "/demo-data/originals/research/" + reference_id + ".docx",
            })
        incoming_dir = library / "incoming-tests"
        for i, source in enumerate(sorted(incoming_dir.glob("*.docx")), 1):
            token = "CH-" + str(i).zfill(2)
            digest = copy_verified(source, destination / "originals" / "research" / (token + ".docx"))
            records["challenge_cases"].append({
                "id": token, "name": source.stem.removeprefix("Incoming - "),
                "sha256": digest, "download": "/demo-data/originals/research/" + token + ".docx",
                "status": "Unassessed research fixture",
            })
        routine_dir = library / "routine-clients"
        for i, source in enumerate(sorted(routine_dir.glob("*.docx")), 1):
            token = "RC-" + str(i).zfill(2)
            digest = copy_verified(source, destination / "originals" / "research" / (token + ".docx"))
            records["routine_clients"].append({
                "id": token, "name": source.stem,
                "sha256": digest, "download": "/demo-data/originals/research/" + token + ".docx",
                "status": "Routine-looking specimen; match not verified",
            })
    write_json(destination / "research.json", records)
    # A separate, explicitly fictional log: never import the private append-only ledger.
    # These topic links are not source-backed past legal decisions or published precedents.
    demo_history = json.loads((ROOT / "dataset" / "review_records" / "demo_decision_log.json").read_text(encoding="utf-8"))
    entries = demo_history.get("records", [])
    if demo_history.get("synthetic") is not True or len(entries) != 300:
        raise ValueError("Demo decision log must contain 300 clearly synthetic entries")
    if len({row.get("id") for row in entries}) != 300 or any(
        row.get("synthetic") is not True
        or row.get("record_status") != "illustrative_unverified"
        or row.get("review_id") not in app.contracts
        or row.get("related_fixed_example_id") not in (*app.historical.keys(), None)
        for row in entries
    ):
        raise ValueError("Demo decision log has invalid IDs, links or provenance")
    write_json(destination / "decision-log.json", demo_history)
    print(
        "Exported 6 working NDA review scenarios plus %d research standards, %d routine-looking clients, %d challenge files."
        % (len(records["references"]), len(records["routine_clients"]), len(records["challenge_cases"]))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "demo-data")
    args = parser.parse_args()
    export(args.out)
