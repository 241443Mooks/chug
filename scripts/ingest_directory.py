"""One scheduled intake pass over a private DOCX drop directory.

Use the same automatic pipeline as browser uploads. A scheduler may run this
command repeatedly; source hashes make repeated delivery idempotent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chug.server import App


def ingest(state_dir: Path, incoming_dir: Path) -> dict:
    if not incoming_dir.is_dir():
        raise ValueError("Incoming directory does not exist")
    app = App(ROOT, state_dir)
    paths = sorted(path for path in incoming_dir.iterdir() if path.is_file() and not path.is_symlink() and path.suffix.lower() == ".docx")
    totals = {"analysed": 0, "awaiting_reference": 0, "blocked_extraction": 0, "duplicate": 0, "failed": 0}
    items = []
    for offset in range(0, len(paths), 20):
        files = [(path.name, path.read_bytes()) for path in paths[offset:offset + 20]]
        batch = app.intake_batch(files)
        items.extend(batch["items"])
        for key, count in batch["counts"].items():
            totals[key] += count
    return {"submitted": len(paths), "counts": totals, "items": items}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--incoming-dir", type=Path, required=True)
    args = parser.parse_args()
    result = ingest(args.state_dir, args.incoming_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["counts"]["failed"] else 0)
