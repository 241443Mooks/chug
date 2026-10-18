"""Append-only local human decision log."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock
from uuid import uuid4

DECISIONS = {"approve", "request_amendment", "reject", "escalate"}


def _append(path, lock, event):
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.lock = Lock()

    def all(self, sha256=None):
        if not self.path.exists():
            return []
        with self.lock:
            with self.path.open(encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle if line.strip()]
        return [event for event in events if event["sha256"] == sha256] if sha256 else events

    def append(self, sha256, filename, reviewer, decision, rationale, finding_ids, conditions="", considered_sources=None, reference_sha256=None):
        if not isinstance(decision, str) or decision not in DECISIONS or not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(rationale, str) or not rationale.strip() or len(reviewer) > 100 or len(rationale) > 2000 or not isinstance(conditions, str) or len(conditions) > 1000:
            raise ValueError("Choose a decision and provide reviewer name and rationale")
        if not isinstance(finding_ids, list) or any(not isinstance(item, str) for item in finding_ids):
            raise ValueError("Invalid finding references")
        considered_sources = considered_sources if considered_sources is not None else []
        if not isinstance(considered_sources, list) or any(not isinstance(item, dict) or not isinstance(item.get("finding_id"), str) or item["finding_id"] not in finding_ids or not isinstance(item.get("anchor"), str) or not isinstance(item.get("text"), str) for item in considered_sources):
            raise ValueError("Invalid considered source passages")
        if reference_sha256 is not None and (not isinstance(reference_sha256, str) or len(reference_sha256) != 64):
            raise ValueError("Invalid reference identity")
        event = {"id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "sha256": sha256, "filename": filename, "reviewer": reviewer.strip(), "decision": decision, "rationale": rationale.strip(), "conditions": conditions.strip(), "finding_ids": finding_ids, "considered_sources": considered_sources}
        if reference_sha256 is not None:
            event["reference_sha256"] = reference_sha256
        _append(self.path, self.lock, event)
        return event


class KnowledgeLedger:
    """Append-only publication lifecycle; a decision alone never enters retrieval."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()

    def all(self):
        if not self.path.exists():
            return []
        with self.lock:
            with self.path.open(encoding="utf-8") as handle:
                events = [json.loads(line) for line in handle if line.strip()]
        published = {}
        withdrawn = set()
        event_ids = set()
        for event in events:
            if not isinstance(event, dict) or not event.get("id") or event["id"] in event_ids:
                raise ValueError("Knowledge ledger contains a duplicate or invalid event ID")
            event_ids.add(event["id"])
            if event.get("type") == "publish":
                if not all(event.get(key) for key in ("decision_id", "sha256", "document_id", "finding_id", "source_anchor", "source_text", "section_title", "authoriser", "context", "reuse_limits", "timestamp", "decision", "rationale")) or "conditions" not in event or event.get("version") != 1 or event.get("authority_mode") != "self_attested_demo":
                    raise ValueError("Knowledge ledger contains an invalid publication")
                published[event["id"]] = event
            elif event.get("type") == "withdraw":
                if event.get("publication_id") not in published or event["publication_id"] in withdrawn or not all(event.get(key) for key in ("id", "actor", "reason", "timestamp")):
                    raise ValueError("Knowledge ledger contains an invalid withdrawal")
                withdrawn.add(event["publication_id"])
            else:
                raise ValueError("Knowledge ledger contains an unknown event")
        return events

    def active(self):
        events = self.all()
        withdrawn = {event["publication_id"] for event in events if event["type"] == "withdraw"}
        return [event for event in events if event["type"] == "publish" and event["id"] not in withdrawn]

    def publish(self, decision, document_id, finding_id, source, section_title, authoriser, context, reuse_limits, reference_sha256=None):
        if not isinstance(authoriser, str) or not authoriser.strip() or len(authoriser) > 100 or not isinstance(context, str) or not context.strip() or len(context) > 1000 or not isinstance(reuse_limits, str) or not reuse_limits.strip() or len(reuse_limits) > 1000:
            raise ValueError("Provide a demonstration publisher, commercial context and reuse limits")
        with self.lock:
            if any(event["decision_id"] == decision["id"] for event in self.active()):
                raise ValueError("This decision already has an active publication")
            event = {"id": str(uuid4()), "type": "publish", "version": 1, "timestamp": datetime.now(timezone.utc).isoformat(), "decision_id": decision["id"], "sha256": decision["sha256"], "document_id": document_id, "finding_id": finding_id, "source_anchor": source["anchor"], "source_text": source["text"], "section_title": section_title, "decision": decision["decision"], "rationale": decision["rationale"], "conditions": decision.get("conditions", ""), "authoriser": authoriser.strip(), "authority_mode": "self_attested_demo", "context": context.strip(), "reuse_limits": reuse_limits.strip()}
            if reference_sha256 is not None:
                event["reference_sha256"] = reference_sha256
            _append(self.path, self.lock, event)
        return event

    def withdraw(self, publication_id, actor, reason):
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 100 or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise ValueError("Provide a demonstration publisher and withdrawal reason")
        with self.lock:
            if publication_id not in {event["id"] for event in self.active()}:
                raise ValueError("Publication is not active")
            event = {"id": str(uuid4()), "type": "withdraw", "timestamp": datetime.now(timezone.utc).isoformat(), "publication_id": publication_id, "actor": actor.strip(), "reason": reason.strip()}
            _append(self.path, self.lock, event)
        return event
