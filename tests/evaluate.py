"""Isolated, post-analysis evaluation. Runtime never imports this module."""
import csv
from pathlib import Path

from chug.engine import analyse, load_library

ROOT = Path(__file__).resolve().parents[1]
reference, historical, incoming, decisions = load_library(ROOT)
results = {document_id: analyse(reference, document, historical, decisions) for document_id, document in incoming.items()}
expected = list(csv.DictReader((ROOT / "dataset/ground_truth/expected_findings.csv").open(newline="")))
mapping = {"routine": "routine_candidate", "review": "review_required", "escalate": "escalate"}
failures = []
for row in expected:
    ident = row["document_id"]
    actual = results[ident]
    want = mapping[row["expected_review_route"]]
    ok = actual["route"] == want
    print(f"{ident}: expected={want} observed={actual['route']} finding={actual['reason']} result={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(ident)
print(f"Route agreement: {len(expected)-len(failures)}/{len(expected)}")
raise SystemExit(1 if failures else 0)
