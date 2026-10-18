"""Loopback-only web app for synthetic NDA review."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote, urlsplit

from .ai import AIService, AIUnavailable
from .document import extract
from .nda_pack import NDAPack
from .ledger import KnowledgeLedger, Ledger
from .corrections import CorrectionLedger


class App:
    def __init__(self, root: Path, state_dir: Path, pack: NDAPack | None = None):
        self.root = root
        self.state_dir = state_dir
        self.pack = pack if pack is not None else NDAPack()
        self.reference, self.historical, incoming, self.decisions = self.pack.load_library(root)
        self.bundled_reference_sha256 = self.reference["sha256"]
        bundled_path = self.pack.reference_path(root)
        self.references = {self.bundled_reference_sha256: {"document": self.reference, "path": bundled_path, "kind": "bundled"}}
        self._load_references()
        self.active_reference_sha256 = self._load_selection()
        self.contracts = {}
        for document_id, document in incoming.items():
            self.contracts[document_id] = {"document": document, "path": self.pack.incoming_path(root, document_id), "reference_sha256": self.bundled_reference_sha256}
        uploads = state_dir / "uploads"
        if uploads.exists():
            if list(uploads.glob("*.uploading")) or list(uploads.glob("*.recording")):
                raise ValueError("Upload recovery required: interrupted write detected")
            metadata = {path.stem: path for path in uploads.glob("*.json")}
            originals = {path.stem: path for path in uploads.glob("*.docx")}
            if set(metadata) != set(originals):
                raise ValueError("Upload recovery required: original and metadata files do not match")
            for stem, meta_path in metadata.items():
                meta = json.loads(meta_path.read_text())
                path = originals[stem]
                data = path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                if digest != stem or meta.get("sha256") != digest or not meta.get("filename"):
                    raise ValueError("Upload recovery required: source identity mismatch for " + stem)
                bindings = self._bindings(meta, digest)
                document = extract(data, meta["filename"])
                for binding in bindings:
                    if binding["reference_sha256"] not in self.references or binding["id"] in self.contracts:
                        raise ValueError("Upload recovery required: reference binding is unavailable or duplicated")
                    self.contracts[binding["id"]] = {"document": document, "path": path, "reference_sha256": binding["reference_sha256"]}
        self.ledger = Ledger(state_dir / "decisions.jsonl")
        self.knowledge = KnowledgeLedger(state_dir / "knowledge.jsonl")
        self.corrections = CorrectionLedger(state_dir / "corrections.jsonl")
        self.active_precedents()  # Fail visibly on broken publication history or source links.
        self.active_lessons()
        self.ai = AIService()
        self.ai_results = {}

    def _load_references(self):
        directory = self.state_dir / "references"
        if not directory.exists():
            return
        if list(directory.glob("*.uploading")) or list(directory.glob("*.recording")) or list(directory.glob("*.selecting")):
            raise ValueError("Reference recovery required: interrupted write detected")
        metadata = {path.stem: path for path in directory.glob("*.json")}
        originals = {path.stem: path for path in directory.glob("*.docx")}
        if set(metadata) != set(originals):
            raise ValueError("Reference recovery required: original and metadata files do not match")
        for stem, meta_path in metadata.items():
            meta = json.loads(meta_path.read_text())
            data = originals[stem].read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != stem or meta.get("sha256") != digest or not meta.get("filename") or meta.get("kind") != "uploaded_synthetic":
                raise ValueError("Reference recovery required: source identity mismatch")
            document = extract(data, meta["filename"])
            self._validate_reference(document)
            self.references[digest] = {"document": document, "path": originals[stem], "kind": "uploaded_synthetic"}

    def _load_selection(self):
        path = self.state_dir / "reference_selection.json"
        if (self.state_dir / "reference_selection.selecting").exists():
            raise ValueError("Reference recovery required: interrupted selection detected")
        if not path.exists():
            return self.bundled_reference_sha256
        selection = json.loads(path.read_text())
        digest = selection.get("sha256") if isinstance(selection, dict) else None
        if digest not in self.references:
            raise ValueError("Reference selection points to an unavailable original")
        return digest

    def _validate_reference(self, document):
        self.pack.validate_reference(document, self.reference)

    def _bindings(self, meta, digest):
        if "bindings" not in meta:
            if meta.get("id") != "U-" + digest[:10]:
                raise ValueError("Upload recovery required: source identity mismatch for " + digest)
            return [{"id": meta["id"], "reference_sha256": self.bundled_reference_sha256}]
        bindings = meta["bindings"]
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("Upload recovery required: no reference bindings")
        ids = set()
        for binding in bindings:
            ref = binding.get("reference_sha256") if isinstance(binding, dict) else None
            expected = "U-" + digest[:10] if ref == self.bundled_reference_sha256 else "U-" + digest[:10] + "-" + str(ref)[:8]
            if ref not in self.references or binding.get("id") != expected or expected in ids:
                raise ValueError("Upload recovery required: invalid reference binding")
            ids.add(expected)
        return bindings

    def reference_info(self):
        current = self.references[self.active_reference_sha256]
        try:
            intact = hashlib.sha256(current["path"].read_bytes()).hexdigest() == self.active_reference_sha256
        except OSError:
            intact = False
        return {"current": {**current["document"], "kind": current["kind"], "source_integrity": "verified" if intact else "mismatch"}, "available": [{"sha256": sha, "filename": item["document"]["filename"], "kind": item["kind"]} for sha, item in self.references.items()]}

    def select_reference(self, digest):
        if digest not in self.references:
            raise ValueError("Reference not found")
        try:
            intact = hashlib.sha256(self.references[digest]["path"].read_bytes()).hexdigest() == digest
        except OSError:
            intact = False
        if not intact:
            raise ValueError("Reference original is unavailable or changed")
        directory = self.state_dir
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "reference_selection.selecting"
        with temporary.open("w") as handle:
            json.dump({"sha256": digest}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, directory / "reference_selection.json")
        self.active_reference_sha256 = digest
        return self.reference_info()

    def upload_reference(self, data, filename):
        if not isinstance(filename, str) or not filename.lower().endswith(".docx") or len(data) > 2_000_000:
            raise ValueError("Choose one synthetic DOCX under 2 MB")
        document = extract(data, filename)
        self._validate_reference(document)
        digest = document["sha256"]
        if digest in self.references:
            return self.select_reference(digest)
        directory = self.state_dir / "references"
        directory.mkdir(parents=True, exist_ok=True)
        original = directory / (digest + ".docx")
        metadata = directory / (digest + ".json")
        temporary = directory / (digest + ".uploading")
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, original)
        temporary = directory / (digest + ".recording")
        with temporary.open("x") as handle:
            json.dump({"sha256": digest, "filename": filename, "kind": "uploaded_synthetic"}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, metadata)
        self.references[digest] = {"document": document, "path": original, "kind": "uploaded_synthetic"}
        return self.select_reference(digest)

    def active_precedents(self):
        decisions = {event["id"]: event for event in self.ledger.all()}
        records = []
        for event in self.knowledge.active():
            item = self.contracts.get(event["document_id"])
            decision = decisions.get(event["decision_id"])
            if not item or not decision or decision["sha256"] != event["sha256"] or decision["decision"] != event["decision"] or decision["rationale"] != event["rationale"] or decision.get("conditions", "") != event["conditions"]:
                raise ValueError("Published precedent has a broken decision or document link; retrieval unavailable")
            document = item["document"]
            reference_sha256 = item["reference_sha256"]
            if event.get("reference_sha256", self.bundled_reference_sha256) != reference_sha256 or decision.get("reference_sha256", self.bundled_reference_sha256) != reference_sha256:
                raise ValueError("Published precedent has a broken reference link; retrieval unavailable")
            source = next((unit for unit in document["units"] if unit["anchor"] == event["source_anchor"]), None)
            try:
                source_matches = hashlib.sha256(item["path"].read_bytes()).hexdigest() == event["sha256"]
            except OSError:
                source_matches = False
            if document["sha256"] != event["sha256"] or document["coverage"]["status"] != "complete" or not source_matches or not source or source["text"] != event["source_text"]:
                raise ValueError("Published precedent source is unavailable or changed; retrieval unavailable")
            considered = decision.get("considered_sources", [])
            evidence_matches = any(row.get("finding_id") == event["finding_id"] and row.get("anchor") == event["source_anchor"] and row.get("text") == event["source_text"] for row in considered)
            if event["finding_id"] not in decision["finding_ids"] or not evidence_matches or decision["timestamp"] > event["timestamp"]:
                raise ValueError("Published precedent no longer matches its reviewed evidence; retrieval unavailable")
            records.append({**event, "document": document, "source": source, "reference_sha256": reference_sha256})
        return records

    def publish(self, document_id, decision_id, source_anchor, authoriser, context, reuse_limits):
        detail = self.detail(document_id)
        if detail["analysis"]["route"] == "blocked_extraction":
            raise ValueError("Complete extraction and source integrity are required before publication")
        decision = next((event for event in detail["history"] if event["id"] == decision_id), None)
        if not decision:
            raise ValueError("Choose a recorded decision for this exact document")
        evidence = next((row for row in decision.get("considered_sources", []) if row["anchor"] == source_anchor and row["finding_id"] in decision["finding_ids"]), None)
        source = next((unit for unit in detail["document"]["units"] if unit["anchor"] == source_anchor), None)
        if not evidence or not source or source["text"] != evidence["text"]:
            raise ValueError("Choose a source passage from a finding considered in this decision")
        section_title = self.pack.section_title(detail["document"], source_anchor)
        if not section_title:
            raise ValueError("The source passage has no reviewable section")
        return self.knowledge.publish(decision, document_id, evidence["finding_id"], source, section_title, authoriser, context, reuse_limits, self.contracts[document_id]["reference_sha256"])

    def withdraw(self, publication_id, actor, reason):
        return self.knowledge.withdraw(publication_id, actor, reason)

    def correction_history(self, document_id):
        item = self.contracts[document_id]
        events = self.corrections.all()
        corrections = [row for row in events if row["type"] == "correction" and row["document_sha256"] == item["document"]["sha256"] and row["reference_sha256"] == item["reference_sha256"]]
        return [{**row, "publications": [{**pub, "status": "withdrawn" if any(end["type"] == "withdraw" and end["publication_id"] == pub["id"] for end in events) else "active"} for pub in events if pub["type"] == "publish" and pub["correction_id"] == row["id"]]} for row in corrections]

    def active_lessons(self):
        lessons = []
        for pair in self.corrections.active():
            correction = pair["correction"]
            item = self.contracts.get(correction["document_id"])
            if not item or item["document"]["sha256"] != correction["document_sha256"] or item["reference_sha256"] != correction["reference_sha256"]:
                raise ValueError("Published correction has a broken document or reference link")
            try:
                intact = hashlib.sha256(item["path"].read_bytes()).hexdigest() == correction["document_sha256"] and hashlib.sha256(self.references[correction["reference_sha256"]]["path"].read_bytes()).hexdigest() == correction["reference_sha256"]
            except (OSError, KeyError):
                intact = False
            source = next((unit for unit in item["document"]["units"] if unit["anchor"] == correction["source_anchor"] and unit["text"] == correction["source_text"]), None) if correction["source_anchor"] else None
            reference = next((unit for unit in self.references[correction["reference_sha256"]]["document"]["units"] if unit["anchor"] == correction["reference_anchor"] and unit["text"] == correction["reference_text"]), None) if correction["reference_anchor"] else None
            if not intact or (correction["source_anchor"] and not source) or (correction["reference_anchor"] and not reference):
                raise ValueError("Published correction source evidence is unavailable or changed")
            lessons.append(pair)
        return lessons

    def record_correction(self, document_id, finding_id, source_anchor, reference_anchor, relationship, explanation, reviewer):
        detail = self.detail(document_id)
        if detail["analysis"]["route"] == "blocked_extraction":
            raise ValueError("Comparison correction requires complete source extraction")
        finding = next((row for row in detail["analysis"]["findings"] if row["id"] == finding_id), None)
        if not finding and (finding_id not in (None, "") or relationship != "overlooked_exception"):
            raise ValueError("Choose a current comparison finding")
        sources = {unit["anchor"]: unit for unit in detail["document"]["units"]}
        references = {unit["anchor"]: unit for unit in detail["reference"]["units"]}
        if source_anchor and source_anchor not in sources or reference_anchor and reference_anchor not in references or not source_anchor and not reference_anchor:
            raise ValueError("Choose valid source or reference evidence")
        return self.corrections.record(document_id, detail["document"]["sha256"], detail["reference"]["sha256"], finding, sources.get(source_anchor), references.get(reference_anchor), relationship, explanation, reviewer)

    def publish_correction(self, correction_id, publisher, context, reuse_limits):
        correction = next((row for row in self.corrections.all() if row["type"] == "correction" and row["id"] == correction_id), None)
        if not correction or correction["document_id"] not in self.contracts:
            raise ValueError("Correction not found")
        detail = self.detail(correction["document_id"])
        if detail["analysis"]["route"] == "blocked_extraction":
            raise ValueError("Cannot publish a correction with broken source integrity")
        if correction["document_sha256"] != detail["document"]["sha256"] or correction["reference_sha256"] != detail["reference"]["sha256"]:
            raise ValueError("Correction source or reference identity changed")
        source = next((unit for unit in detail["document"]["units"] if unit["anchor"] == correction["source_anchor"] and unit["text"] == correction["source_text"]), None) if correction["source_anchor"] else None
        reference = next((unit for unit in detail["reference"]["units"] if unit["anchor"] == correction["reference_anchor"] and unit["text"] == correction["reference_text"]), None) if correction["reference_anchor"] else None
        if (correction["source_anchor"] and not source) or (correction["reference_anchor"] and not reference) or not source and not reference:
            raise ValueError("Correction source evidence is unavailable or changed")
        return self.corrections.publish(correction_id, publisher, context, reuse_limits)

    def correction_lessons(self, document_id, findings):
        item = self.contracts[document_id]
        matches = []
        for pair in self.active_lessons():
            past = pair["correction"]
            if past["reference_sha256"] != item["reference_sha256"] or past["document_sha256"] == item["document"]["sha256"]:
                continue
            for finding in findings:
                overlap = self.pack.shared_terms(past["source_text"] or past["reference_text"], " ".join(unit["text"] for unit in finding["sources"]) or (finding["reference"]["text"] if finding["reference"] else ""))
                if len(overlap) < 3:
                    continue
                matches.append({"finding_id": finding["id"], "publication_id": pair["publication"]["id"], "previous_document_id": past["document_id"], "previous_source_anchor": past["source_anchor"], "previous_source_text": past["source_text"], "previous_reference_anchor": past["reference_anchor"], "relationship": past["relationship"], "explanation": past["explanation"], "reviewer": past["reviewer"], "publisher": pair["publication"]["publisher"], "context": pair["publication"]["context"], "reuse_limits": pair["publication"]["reuse_limits"], "match_basis": "shared terms: " + ", ".join(overlap[:5]), "applicability": "unverified; compare the current exception and commercial context"})
        return matches[:10]

    def analysis(self, document_id):
        item = self.contracts[document_id]
        document = item["document"]
        reference_sha256 = item["reference_sha256"]
        reference_item = self.references[reference_sha256]
        reference = reference_item["document"]
        try:
            source_matches = hashlib.sha256(item["path"].read_bytes()).hexdigest() == document["sha256"]
            reference_matches = hashlib.sha256(reference_item["path"].read_bytes()).hexdigest() == reference_sha256
        except OSError:
            source_matches = False
            reference_matches = False
        if not source_matches or not reference_matches:
            issue = "Original source or chosen reference is unavailable or changed after intake; analysis cannot be trusted"
            damaged = {**document, "coverage": {**document["coverage"], "status": "blocked", "issues": [*document["coverage"]["issues"], issue]}}
            report = self.pack.blocked_analysis(reference, damaged)
            report["assurance"]["source_integrity"]["status"] = "mismatch" if not source_matches else "identified"
            report["assurance"]["limitations"].append("Chosen reference integrity: " + ("verified" if reference_matches else "mismatch"))
            report["reference_sha256"] = reference_sha256
            return report
        published = [record for record in self.active_precedents() if record["reference_sha256"] == reference_sha256]
        report = self.pack.analyse(reference, document, self.historical, self.decisions, published, self.reference)
        unresolved = [row for row in self.correction_history(document_id) if row["relationship"] == "overlooked_exception"]
        if unresolved:
            report["assurance"]["limitations"].append("A reviewer reported a possibly missed exception; inspect the correction history and cited original before deciding.")
            if report["route"] == "routine_candidate":
                report["route"] = "review_required"
                report["reason"] = "Reviewer reported a possibly missed exception"
        report["reference_sha256"] = reference_sha256
        report["comparison_lessons"] = self.correction_lessons(document_id, report["findings"])
        return report

    def queue(self):
        latest = {}
        for event in self.ledger.all():
            latest[(event["sha256"], event.get("reference_sha256", self.bundled_reference_sha256))] = event
        rows = []
        for document_id, item in self.contracts.items():
            document = item["document"]
            review = self.analysis(document_id)
            rows.append({"id": document_id, "filename": document["filename"], "display_name": self.pack.display_name(document), "sha256": document["sha256"], "reference_sha256": item["reference_sha256"], "route": review["route"], "reason": review["reason"], "findings_count": len(review["findings"]), "latest_decision": latest.get((document["sha256"], item["reference_sha256"]))})
        return sorted(rows, key=lambda row: (-self.pack.route_order[row["route"]], row["id"]))

    def detail(self, document_id):
        item = self.contracts[document_id]
        document = item["document"]
        reference_sha256 = item["reference_sha256"]
        history = [event for event in self.ledger.all(document["sha256"]) if event.get("reference_sha256", self.bundled_reference_sha256) == reference_sha256]
        knowledge_events = self.knowledge.all()
        publications = []
        for event in knowledge_events:
            if event["type"] != "publish" or event["sha256"] != document["sha256"] or event.get("reference_sha256", self.bundled_reference_sha256) != reference_sha256:
                continue
            withdrawal = next((row for row in knowledge_events if row["type"] == "withdraw" and row["publication_id"] == event["id"]), None)
            publications.append({**event, "status": "withdrawn" if withdrawal else "active", "withdrawal": withdrawal})
        analysis = self.analysis(document_id)
        analysis["assurance"]["human_review"] = {"status": "recorded" if history else "not recorded", "last_decision": history[-1]["decision"] if history else None, "events": len(history)}
        return {"id": document_id, "display_name": self.pack.display_name(document), "document": document, "reference": self.references[reference_sha256]["document"], "reference_kind": self.references[reference_sha256]["kind"], "analysis": analysis, "history": history, "publications": publications, "corrections": self.correction_history(document_id), "ai": self.ai.status(), "ai_results": self.ai_results.get((document["sha256"], reference_sha256), [])}

    def upload(self, data, filename):
        if not isinstance(filename, str) or not filename.lower().endswith(".docx") or len(data) > 2_000_000:
            raise ValueError("Choose one synthetic DOCX under 2 MB")
        document = extract(data, filename)
        reference_sha256 = self.active_reference_sha256
        document_id = "U-" + document["sha256"][:10] + ("" if reference_sha256 == self.bundled_reference_sha256 else "-" + reference_sha256[:8])
        if document_id in self.contracts and (self.contracts[document_id]["document"]["sha256"] != document["sha256"] or self.contracts[document_id]["reference_sha256"] != reference_sha256):
            raise ValueError("Upload ID collision; source cannot be safely associated with this reference")
        target = self.state_dir / "uploads"
        target.mkdir(parents=True, exist_ok=True)
        file_path = target / (document["sha256"] + ".docx")
        if not file_path.exists():
            temporary = target / (document["sha256"] + ".uploading")
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, file_path)
        elif hashlib.sha256(file_path.read_bytes()).hexdigest() != document["sha256"]:
            raise ValueError("Existing uploaded original does not match its source hash")
        meta_path = target / (document["sha256"] + ".json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta.get("sha256") != document["sha256"] or not meta.get("filename"):
                raise ValueError("Existing upload metadata does not match original")
            bindings = self._bindings(meta, document["sha256"])
            if any(binding["reference_sha256"] == reference_sha256 for binding in bindings):
                return document_id
        else:
            bindings = []
        new_meta = {"sha256": document["sha256"], "filename": meta["filename"] if meta_path.exists() else document["filename"], "bindings": [*bindings, {"id": document_id, "reference_sha256": reference_sha256}]}
        temporary = target / (document["sha256"] + ".recording")
        with temporary.open("x") as handle:
            json.dump(new_meta, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, meta_path)
        self.contracts[document_id] = {"document": extract(data, new_meta["filename"]), "path": file_path, "reference_sha256": reference_sha256}
        return document_id


class Handler(BaseHTTPRequestHandler):
    app: App
    server_version = "ChugChug"
    sys_version = ""
    online_mode = False
    access_username = ""
    access_password = ""
    public_origin = ""

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _authorised(self):
        if not self.online_mode:
            return True
        value = self.headers.get("Authorization", "")
        scheme, separator, token = value.partition(" ")
        try:
            supplied = base64.b64decode(token, validate=True) if separator and scheme.lower() == "basic" else b""
        except (ValueError, binascii.Error):
            supplied = b""
        username, colon, password = supplied.partition(b":")
        valid_user = hmac.compare_digest(username, self.access_username.encode("utf-8"))
        valid_password = hmac.compare_digest(password, self.access_password.encode("utf-8"))
        if colon and valid_user and valid_password:
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="ChugChug private demo", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Authentication required\n")
        return False

    def _same_origin(self):
        if not self.online_mode:
            return True
        origin = self.headers.get("Origin", "")
        if origin == self.public_origin:
            return True
        self._error(403, "Request origin is not allowed")
        return False

    def log_message(self, fmt, *args):
        # Do not log submitted contract text, reviewer rationales or keys.
        print("HTTP", self.address_string(), fmt % args)

    def _json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message):
        self._json({"error": message}, status)

    def _body(self, limit=2_100_000):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > limit:
            raise ValueError("Request size is missing or exceeds the local limit")
        return self.rfile.read(length)

    def _multipart_docx(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data;"):
            raise ValueError("Choose a DOCX file")
        data = self._body()
        message = BytesParser(policy=policy.default).parsebytes(b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode() + b"\r\n\r\n" + data)
        files = [part for part in message.iter_parts() if part.get_param("name", header="content-disposition") == "file"] if message.is_multipart() else []
        if len(files) != 1:
            raise ValueError("Choose one DOCX file")
        filename = files[0].get_filename() or "uploaded.docx"
        if not filename.lower().endswith(".docx"):
            raise ValueError("DOCX only")
        return files[0].get_payload(decode=True), filename

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            return self.wfile.write(b"ok\n")
        if not self._authorised():
            return
        if path == "/api/queue":
            try:
                return self._json({"items": self.app.queue()})
            except ValueError as exc:
                return self._error(409, str(exc))
        if path == "/api/reference":
            return self._json(self.app.reference_info())
        historical = re.fullmatch(r"/api/history/([A-Za-z0-9_-]+)(/original)?", path)
        if historical:
            document_id = historical.group(1)
            document = self.app.historical.get(document_id)
            if not document:
                return self._error(404, "Historical case not found")
            source = self.app.pack.historical_path(self.app.root, document_id)
            try:
                data = source.read_bytes() if source else b""
            except OSError:
                data = b""
            if hashlib.sha256(data).hexdigest() != document["sha256"]:
                return self._error(409, "Historical source identity changed")
            if historical.group(2):
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", 'attachment; filename="historical-contract.docx"')
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return self.wfile.write(data)
            return self._json({"document": document, "decision": self.app.decisions[document_id]})
        reference_original = re.fullmatch(r"/api/references/([0-9a-f]{64})/original", path)
        if reference_original:
            item = self.app.references.get(reference_original.group(1))
            if not item:
                return self._error(404, "Reference not found")
            try:
                data = item["path"].read_bytes()
            except OSError:
                return self._error(409, "Reference original unavailable")
            if hashlib.sha256(data).hexdigest() != reference_original.group(1):
                return self._error(409, "Reference original identity changed")
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.send_header("Content-Disposition", 'attachment; filename="reference.docx"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(data)
        if path.startswith("/api/contracts/"):
            parts = path.split("/")
            if len(parts) not in (4, 5) or parts[3] not in self.app.contracts:
                return self._error(404, "Contract not found")
            document_id = parts[3]
            if len(parts) == 4:
                try:
                    return self._json(self.app.detail(document_id))
                except ValueError as exc:
                    return self._error(409, str(exc))
            if parts[4] != "original":
                return self._error(404, "Not found")
            try:
                data = self.app.contracts[document_id]["path"].read_bytes()
            except OSError:
                return self._error(409, "Original source unavailable; stop review and inspect local files")
            if hashlib.sha256(data).hexdigest() != self.app.contracts[document_id]["document"]["sha256"]:
                return self._error(409, "Original source identity changed; stop review and inspect local files")
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.send_header("Content-Disposition", 'attachment; filename="contract.docx"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(data)
        if path in ("/", "/index.html", "/app.js", "/styles.css", "/decision-log.html", "/decision-log.js", "/decision-log.css", "/demo-data/decision-log.json"):
            filename = "index.html" if path == "/" else path[1:]
            content_type = "application/json" if filename.endswith("json") else "text/html" if filename.endswith("html") else "text/javascript" if filename.endswith("js") else "text/css"
            data = (self.app.root / "web" / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        return self._error(404, "Not found")

    def do_POST(self):
        if not self._authorised():
            return
        if not self._same_origin():
            return
        path = urlparse(self.path).path
        try:
            if path == "/api/upload":
                data, filename = self._multipart_docx()
                return self._json({"id": self.app.upload(data, filename)}, 201)
            if path == "/api/reference/upload":
                data, filename = self._multipart_docx()
                return self._json(self.app.upload_reference(data, filename), 201)
            body = json.loads(self._body(100_000))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object")
            if path == "/api/reference/select":
                return self._json(self.app.select_reference(body.get("sha256")))
            if path == "/api/corrections":
                document_id = body.get("document_id")
                if document_id not in self.app.contracts:
                    return self._error(404, "Contract not found")
                event = self.app.record_correction(document_id, body.get("finding_id"), body.get("source_anchor", ""), body.get("reference_anchor", ""), body.get("relationship"), body.get("explanation", ""), body.get("reviewer", ""))
                return self._json(event, 201)
            if path == "/api/correction-lessons":
                if body.get("role") != "demo_legal_reviewer" or body.get("acknowledged") is not True:
                    raise ValueError("Confirm the local demonstration publisher role and responsibility")
                return self._json(self.app.publish_correction(body.get("correction_id"), body.get("publisher", ""), body.get("context", ""), body.get("reuse_limits", "")), 201)
            correction_withdrawal = re.fullmatch(r"/api/correction-lessons/([0-9a-f-]+)/withdraw", path)
            if correction_withdrawal:
                if body.get("role") != "demo_legal_reviewer" or body.get("acknowledged") is not True:
                    raise ValueError("Confirm the local demonstration publisher role and responsibility")
                return self._json(self.app.corrections.withdraw(correction_withdrawal.group(1), body.get("actor", ""), body.get("reason", "")), 201)
            if path == "/api/decisions":
                document_id = body["document_id"]
                if not isinstance(document_id, str):
                    raise ValueError("Invalid contract ID")
                if document_id not in self.app.contracts:
                    return self._error(404, "Contract not found")
                detail = self.app.detail(document_id)
                valid_ids = {f["id"] for f in detail["analysis"]["findings"]}
                finding_ids = body.get("finding_ids", [])
                if not isinstance(finding_ids, list) or not set(finding_ids).issubset(valid_ids):
                    raise ValueError("Unknown finding reference")
                doc = detail["document"]
                considered_sources = [{"finding_id": finding["id"], "anchor": source["anchor"], "text": source["text"]} for finding in detail["analysis"]["findings"] if finding["id"] in finding_ids for source in finding["sources"]]
                event = self.app.ledger.append(doc["sha256"], doc["filename"], body.get("reviewer", ""), body.get("decision", ""), body.get("rationale", ""), finding_ids, body.get("conditions", ""), considered_sources, detail["reference"]["sha256"])
                return self._json(event, 201)
            if path == "/api/precedents":
                if body.get("role") != "demo_legal_reviewer" or body.get("acknowledged") is not True:
                    raise ValueError("Confirm the local demonstration publisher role and responsibility")
                document_id = body["document_id"]
                if not isinstance(document_id, str):
                    raise ValueError("Invalid contract ID")
                if document_id not in self.app.contracts:
                    return self._error(404, "Contract not found")
                event = self.app.publish(document_id, body["decision_id"], body["source_anchor"], body.get("authoriser", ""), body.get("context", ""), body.get("reuse_limits", ""))
                return self._json(event, 201)
            withdrawal = re.fullmatch(r"/api/precedents/([0-9a-f-]+)/withdraw", path)
            if withdrawal:
                if body.get("role") != "demo_legal_reviewer" or body.get("acknowledged") is not True:
                    raise ValueError("Confirm the local demonstration publisher role and responsibility")
                return self._json(self.app.withdraw(withdrawal.group(1), body.get("actor", ""), body.get("reason", "")), 201)
            if path == "/api/ai":
                document_id = body["document_id"]
                if document_id not in self.app.contracts:
                    return self._error(404, "Contract not found")
                detail = self.app.detail(document_id)
                finding = next((f for f in detail["analysis"]["findings"] if f["id"] == body.get("finding_id")), None)
                if not finding:
                    raise ValueError("Choose a source-linked changed clause")
                result = self.app.ai.analyse(detail["document"]["sha256"], finding, detail["reference"])
                self.app.ai_results.setdefault((detail["document"]["sha256"], detail["reference"]["sha256"]), []).append(result)
                return self._json(result, 201)
        except (ValueError, KeyError, json.JSONDecodeError, AIUnavailable) as exc:
            return self._error(400, str(exc))
        return self._error(404, "Not found")

    def handle_expect_100(self):
        if not self._authorised() or not self._same_origin():
            return False
        return super().handle_expect_100()


def main():
    parser = argparse.ArgumentParser()
    online_mode = os.environ.get("CHUGCHUG_ONLINE", "").strip() == "1"
    default_host = "0.0.0.0" if online_mode else "127.0.0.1"
    parser.add_argument("--host", default=os.environ.get("CHUGCHUG_HOST", default_host))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--state-dir", type=Path, default=Path(os.environ.get("CHUGCHUG_STATE_DIR", ".chugchug-data")))
    args = parser.parse_args()
    if online_mode:
        username = os.environ.get("CHUGCHUG_ACCESS_USERNAME", "")
        password = os.environ.get("CHUGCHUG_ACCESS_PASSWORD", "")
        origin = os.environ.get("CHUGCHUG_PUBLIC_ORIGIN", "")
        parsed_origin = urlsplit(origin)
        if not username or ":" in username or not password or len(password) < 24:
            parser.error("online mode requires an access username and a password of at least 24 characters")
        if parsed_origin.scheme != "https" or not parsed_origin.hostname or parsed_origin.username or parsed_origin.password or parsed_origin.path not in ("", "/") or parsed_origin.query or parsed_origin.fragment:
            parser.error("online mode requires CHUGCHUG_PUBLIC_ORIGIN to be an HTTPS origin, such as https://review.example.com")
        try:
            origin_port = parsed_origin.port
        except ValueError:
            parser.error("CHUGCHUG_PUBLIC_ORIGIN contains an invalid port")
        origin_host = parsed_origin.hostname.lower()
        if ":" in origin_host:
            origin_host = "[" + origin_host + "]"
        public_origin = "https://" + origin_host + (":" + str(origin_port) if origin_port and origin_port != 443 else "")
        Handler.online_mode = True
        Handler.access_username = username
        Handler.access_password = password
        Handler.public_origin = public_origin
        if args.host != "0.0.0.0":
            parser.error("online mode must bind to the container interface; use --host 0.0.0.0")
    root = Path(__file__).resolve().parent.parent
    Handler.app = App(root, args.state_dir.resolve())
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("ChugChug synthetic review listening on %s:%d" % (args.host, args.port), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
