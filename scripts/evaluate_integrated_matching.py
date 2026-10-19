"""Evaluate frozen captures only after the HTTP runner has finished.

This evaluator is not imported by the application or intake runner.
Usage: python3 scripts/evaluate_integrated_matching.py KEY CAPTURE OUTPUT
"""
import argparse
import hashlib
import json
from pathlib import Path


def evaluate(key_path, capture_path, output):
    key = json.loads(key_path.read_text())
    captured = json.loads(capture_path.read_text())
    by_name = {row["incoming"]["filename"]: row for row in captured["captures"]}
    counts = dict.fromkeys(("correct_match", "correct_abstention", "wrong_match", "unnecessary_abstention"), 0)
    rows = []
    for expected in key:
        actual = by_name[expected["filename"]]
        assert actual["incoming"]["sha256"] == expected["sha256"]
        reference = expected["expected_reference_source"]
        expected_sha = hashlib.sha256(Path(reference).read_bytes()).hexdigest() if reference else None
        selected_sha = actual["reference"]["sha256"]
        if selected_sha:
            outcome = "correct_match" if selected_sha == expected_sha and actual["family"] == expected["expected_family"] else "wrong_match"
        else:
            outcome = "correct_abstention" if expected_sha is None else "unnecessary_abstention"
        counts[outcome] += 1
        rows.append({"filename": expected["filename"], "source": expected["source"],
                     "incoming_sha256": expected["sha256"], "expected_reference_sha256": expected_sha,
                     "selected_reference_id": actual["reference"]["reference_id"], "selected_reference_sha256": selected_sha,
                     "expected_family": expected["expected_family"], "family": actual["family"],
                     "matching_status": actual["matching"]["proposal"]["status"],
                     "comparison_status": actual["comparison"]["status"], "outcome": outcome, "reason": actual["reason"]})
    result = {"key_sha256": hashlib.sha256(key_path.read_bytes()).hexdigest(),
              "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
              "counts": counts, "rows": rows}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(counts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    evaluate(args.key, args.capture, args.output)
