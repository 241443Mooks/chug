"""Append-only reviewer corrections and separately authorised reusable lessons.

A comparison correction is an observation about Chug's analysis, never a
contract decision. The ledger is intentionally small and rebuilds its active
view from the event stream rather than maintaining a second mutable index.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

RELATIONSHIPS = {"wrong_pair", "equivalent_candidate", "partial_overlap", "material_difference", "overlooked_exception", "unsure"}


def _append(path: Path, event):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


class CorrectionLedger:
    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()

    def all(self):
        if not self.path.exists():
            return []
        with self.lock:
            with self.path.open(encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle if line.strip()]
        corrections = {}
        publications = {}
        withdrawn = set()
        ids = set()
        for event in events:
            if not isinstance(event, dict) or not event.get("id") or event["id"] in ids or event.get("version") != 1:
                raise ValueError("Correction ledger has an invalid or duplicate event")
            ids.add(event["id"])
            kind = event.get("type")
            if kind == "correction":
                required = ("timestamp", "document_id", "document_sha256", "reference_sha256", "finding_id", "proposed_category", "source_anchor", "source_text", "reference_anchor", "reference_text", "relationship", "explanation", "reviewer")
                if not all(key in event for key in required) or event["relationship"] not in RELATIONSHIPS:
                    raise ValueError("Correction ledger has an invalid correction")
                corrections[event["id"]] = event
            elif kind == "publish":
                if event.get("correction_id") not in corrections or not all(event.get(key) for key in ("timestamp", "publisher", "context", "reuse_limits")) or event.get("authority_mode") != "self_attested_demo":
                    raise ValueError("Correction publication has no valid source correction")
                publications[event["id"]] = event
            elif kind == "withdraw":
                if event.get("publication_id") not in publications or event["publication_id"] in withdrawn or not all(event.get(key) for key in ("timestamp", "actor", "reason")):
                    raise ValueError("Correction withdrawal is invalid")
                withdrawn.add(event["publication_id"])
            else:
                raise ValueError("Correction ledger has an unknown event")
        return events

    def active(self):
        events = self.all()
        corrections = {row["id"]: row for row in events if row["type"] == "correction"}
        withdrawn = {row["publication_id"] for row in events if row["type"] == "withdraw"}
        return [{"publication": row, "correction": corrections[row["correction_id"]]} for row in events if row["type"] == "publish" and row["id"] not in withdrawn]

    def record(self, document_id, document_sha256, reference_sha256, finding, source, reference, relationship, explanation, reviewer):
        if relationship not in RELATIONSHIPS or not isinstance(explanation, str) or not explanation.strip() or len(explanation) > 2000 or not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 100:
            raise ValueError("Choose a comparison correction and explain it with a reviewer name")
        event = {"id": str(uuid4()), "type": "correction", "version": 1, "timestamp": datetime.now(timezone.utc).isoformat(), "document_id": document_id, "document_sha256": document_sha256, "reference_sha256": reference_sha256, "finding_id": finding["id"] if finding else None, "proposed_category": finding["category"] if finding else "no_finding", "source_anchor": source["anchor"] if source else "", "source_text": source["text"] if source else "", "reference_anchor": reference["anchor"] if reference else "", "reference_text": reference["text"] if reference else "", "relationship": relationship, "explanation": explanation.strip(), "reviewer": reviewer.strip()}
        with self.lock:
            _append(self.path, event)
        return event

    def publish(self, correction_id, publisher, context, reuse_limits):
        if any(not isinstance(value, str) or not value.strip() or len(value) > limit for value, limit in ((publisher, 100), (context, 1000), (reuse_limits, 1000))):
            raise ValueError("Provide a demonstration publisher, context and limits on reuse")
        with self.lock:
            events = self.all()
            if correction_id not in {row["id"] for row in events if row["type"] == "correction"}:
                raise ValueError("Correction not found")
            if any(row["correction"]["id"] == correction_id for row in self.active()):
                raise ValueError("Correction already has an active publication")
            event = {"id": str(uuid4()), "type": "publish", "version": 1, "timestamp": datetime.now(timezone.utc).isoformat(), "correction_id": correction_id, "publisher": publisher.strip(), "context": context.strip(), "reuse_limits": reuse_limits.strip(), "authority_mode": "self_attested_demo"}
            _append(self.path, event)
        return event

    def withdraw(self, publication_id, actor, reason):
        if any(not isinstance(value, str) or not value.strip() or len(value) > limit for value, limit in ((actor, 100), (reason, 1000))):
            raise ValueError("Provide an actor and withdrawal reason")
        with self.lock:
            if publication_id not in {row["publication"]["id"] for row in self.active()}:
                raise ValueError("Correction lesson is not active")
            event = {"id": str(uuid4()), "type": "withdraw", "version": 1, "timestamp": datetime.now(timezone.utc).isoformat(), "publication_id": publication_id, "actor": actor.strip(), "reason": reason.strip()}
            _append(self.path, event)
        return event
