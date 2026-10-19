"""Loopback-only web app for synthetic NDA review."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote, quote

from .ai import AIService, AIUnavailable
from .document import extract
from .nda_pack import NDAPack
from .customer_order_review import CustomerOrderReview
from .customer_order_pack import CustomerOrderPack
from .ledger import FindingAssessmentLedger, ReviewFlagLedger, IntakeConfirmationLedger, KnowledgeLedger, Ledger
from .corrections import CorrectionLedger
from .reference_registry import load_registry, propose_reference, uploaded_reference_metadata


class App:
    def __init__(self, root: Path, state_dir: Path, pack: NDAPack | None = None):
        self.root = root
        self.state_dir = state_dir
        self.pack = pack if pack is not None else NDAPack()
        self.reference, self.historical, incoming, self.decisions = self.pack.load_library(root)
        self.bundled_reference_sha256 = self.reference["sha256"]
        bundled_path = self.pack.reference_path(root)
        self.references = {self.bundled_reference_sha256: {"document": self.reference, "path": bundled_path, "kind": "bundled", "family": "nda"}}
        self.reference_library = {}
        self._load_reference_catalogue(bundled_path)
        self._load_references()
        self._load_match_intakes()
        self.intakes = {}
        self._load_intakes()
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
        self.finding_assessments = FindingAssessmentLedger(state_dir / "finding-assessments.jsonl")
        self.review_flags = ReviewFlagLedger(state_dir / "review-flags.jsonl")
        self.intake_confirmations = IntakeConfirmationLedger(state_dir / "intake_confirmations.jsonl")
        self.intake_confirmations.all()
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
        originals = {path.stem: path for path in directory.iterdir() if path.is_file() and path.suffix not in {".json", ".uploading", ".recording"}}
        if set(metadata) != set(originals):
            raise ValueError("Reference recovery required: original and metadata files do not match")
        for stem, meta_path in metadata.items():
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("Reference recovery required: metadata is unreadable for " + stem) from exc
            record_hash = meta.pop("record_sha256", None)
            if record_hash:
                expected_record_hash = hashlib.sha256(json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                if record_hash != expected_record_hash:
                    raise ValueError("Reference recovery required: metadata integrity mismatch")
            elif "family" in meta:
                raise ValueError("Reference recovery required: metadata integrity record is missing")
            data = originals[stem].read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != stem or meta.get("sha256") != digest or not meta.get("filename") or meta.get("kind") not in (None, "uploaded_synthetic"):
                raise ValueError("Reference recovery required: source identity mismatch")
            document = extract(data, meta["filename"])
            try:
                generated = uploaded_reference_metadata(document, meta.get("display_name") or Path(meta["filename"]).stem, meta.get("version", "1.0"))
            except ValueError as exc:
                raise ValueError("Reference recovery required: " + str(exc)) from exc
            if meta.get("family") and meta["family"] != generated["family"]:
                raise ValueError("Reference recovery required: family metadata does not match source")
            if meta.get("reference_id", generated["reference_id"]) != generated["reference_id"]:
                raise ValueError("Reference recovery required: reference ID does not match source")
            status = meta.get("status", generated["status"])
            legacy_status = status == "registered_for_evaluation" and meta.get("approval_status", "unapproved") == "unapproved"
            if legacy_status:
                status = "active"  # PR #11 records pre-governance uploads; the controlled upload is the authorization boundary.
            if status not in {"active", "superseded", "withdrawn"}:
                raise ValueError("Reference recovery required: uploaded reference status is invalid")
            if meta.get("provenance", "locally_uploaded_synthetic_reference") != "locally_uploaded_synthetic_reference":
                raise ValueError("Reference recovery required: uploaded reference provenance is invalid")
            if generated["family"] == "nda":
                self._validate_reference(document)
                self.references[digest] = {"document": document, "path": originals[stem], "kind": "uploaded_synthetic", "family": "nda"}
            metadata = {**generated, **{key: meta[key] for key in generated if key in meta}}
            metadata["status"] = status
            metadata.pop("approval_status", None)
            if isinstance(meta.get("status_history"), list):
                metadata["status_history"] = meta["status_history"]
            metadata["original_filename"] = meta.get("original_filename", meta["filename"])
            metadata["provenance"] = meta.get("provenance", "locally_uploaded_synthetic_reference")
            if legacy_status:
                history = list(meta.get("status_history", []))
                history.append({"from": "registered_for_evaluation", "to": "active", "reason": "Migrated pre-governance PR #11 upload through the fictional controlled Legal upload flow", "timestamp": datetime.now(timezone.utc).isoformat()})
                meta["status"] = "active"
                meta.pop("approval_status", None)
                meta["status_history"] = history
                meta["record_sha256"] = hashlib.sha256(json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                migration = meta_path.with_suffix(".recording")
                with migration.open("x") as handle:
                    json.dump(meta, handle, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(migration, meta_path)
                metadata["status_history"] = history
            self.reference_library[metadata["reference_id"]] = {"metadata": metadata, "document": document, "path": originals[stem], "kind": "uploaded_synthetic"}

    def _load_reference_catalogue(self, bundled_path):
        base = {
            "reference_id": "BASE-" + self.bundled_reference_sha256[:12],
            "display_name": "Bundled mutual NDA reference",
            "family": "nda", "variant": None, "deployment": None, "channel": None,
            "direction": None, "purpose": None, "jurisdiction": None,
            "applicability": {name: {"state": "unknown", "value": None, "evidence": []} for name in ("family", "direction", "purpose", "deployment", "channel", "jurisdiction", "variant")},
            "original_filename": self.reference["filename"], "sha256": self.bundled_reference_sha256,
            "version": "bundled", "status": "legacy_nda_baseline",
            "provenance": "bundled_demo_baseline", "extraction": {"status": self.reference["coverage"]["status"], "limitations": list(self.reference["coverage"].get("issues", [])), "passage_count": len(self.reference["units"]), "parts": list(self.reference["coverage"].get("parts", []))},
        }
        base["applicability"]["family"] = {"state": "known", "value": "nda", "evidence": []}
        self.reference_library[base["reference_id"]] = {"metadata": base, "document": self.reference, "path": bundled_path, "kind": "bundled"}
        for record in load_registry(self.root):
            source = record["document"]
            applicability = {}
            for name in ("family", "direction", "purpose", "deployment", "channel", "jurisdiction", "variant"):
                value = record.get(name)
                applicability[name] = {"state": "known" if value is not None else "unknown", "value": value, "evidence": []}
            metadata = {
                "reference_id": record["reference_id"], "display_name": record["display_name"],
                "family": record["family"], "variant": record.get("variant"),
                "deployment": record.get("deployment"), "channel": record.get("channel"),
                "direction": record.get("direction"), "purpose": None,
                "jurisdiction": record.get("jurisdiction"), "scope": record.get("scope"),
                "scope_anchor": record.get("scope_anchor"), "applicability": applicability,
                "original_filename": source["filename"], "sha256": record["sha256"],
                "version": record["version"], "status": "research_candidate",
                "approval_status": "unapproved", "provenance": "verified_research_catalogue",
                "extraction": {"status": source["coverage"]["status"], "limitations": list(source["coverage"].get("issues", [])), "passage_count": len(source["units"]), "parts": list(source["coverage"].get("parts", []))},
            }
            self.reference_library[metadata["reference_id"]] = {"metadata": metadata, "document": source, "path": record["source_path"], "kind": "research_candidate"}

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
        library_item = next((item for item in self.reference_library.values() if item["metadata"].get("sha256") == digest), None)
        if library_item and library_item["metadata"].get("status") in {"superseded", "withdrawn"}:
            return self.bundled_reference_sha256
        return digest

    def _load_match_intakes(self):
        self.match_intakes = {}
        directory = self.state_dir / "reference_matches"
        if not directory.exists():
            return
        if list(directory.glob("*.uploading")) or list(directory.glob("*.recording")):
            raise ValueError("Reference matching recovery required: interrupted write detected")
        metadata = {path.stem: path for path in directory.glob("*.json")}
        originals = {path.stem: path for path in directory.glob("*.docx")}
        if set(metadata) != set(originals):
            raise ValueError("Reference matching recovery required: original and proposal records do not match")
        for digest, meta_path in metadata.items():
            try:
                record = json.loads(meta_path.read_text())
                data = originals[digest].read_bytes()
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("Reference matching recovery required: record is unreadable for " + digest) from exc
            record_hash = record.pop("record_sha256", None)
            actual_record_hash = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != record.get("sha256") or hashlib.sha256(data).hexdigest() != digest or record_hash != actual_record_hash:
                raise ValueError("Reference matching recovery required: source or proposal integrity mismatch for " + digest)
            document = record.get("extracted_document") or extract(data, record.get("filename", ""))
            self._validate_extracted_document(data, document, record.get("filename", ""))
            self.match_intakes[digest] = {"document": document, "path": originals[digest], "record": record}

    def _matching_references(self):
        references = []
        unavailable = []
        for item in self.reference_library.values():
            metadata = item["metadata"]
            if metadata.get("status") in {"superseded", "withdrawn"}:
                references.append({**metadata, "document": item["document"]})
                continue
            if self._library_source_integrity(item) != "verified":
                unavailable.append({"reference_id": metadata["reference_id"], "display_name": metadata["display_name"], "status": metadata.get("status"), "reasons": ["source integrity is not verified"]})
                continue
            references.append({**metadata, "document": item["document"]})
        return references, unavailable

    @staticmethod
    def _validate_extracted_document(data, document, filename=None):
        if not isinstance(data, bytes) or len(data) > 2_000_000 or not isinstance(document, dict):
            raise ValueError("Incoming source or extracted-document record is invalid")
        if not isinstance(document.get("filename"), str) or not document["filename"] or Path(document["filename"]).name != document["filename"] or (filename and document["filename"] != Path(filename).name):
            raise ValueError("Extracted-document filename does not match the incoming source")
        if document.get("sha256") != hashlib.sha256(data).hexdigest() or document.get("size") != len(data):
            raise ValueError("Extracted-document source identity does not match the original bytes")
        if not isinstance(document.get("coverage"), dict) or document["coverage"].get("status") not in {"complete", "blocked"} or not isinstance(document.get("units"), list):
            raise ValueError("Extracted-document record is missing coverage or source units")
        for unit in document["units"]:
            if not isinstance(unit, dict) or not all(isinstance(unit.get(key), str) and unit[key] for key in ("anchor", "part", "text")):
                raise ValueError("Extracted-document source anchors are invalid")
        return document

    def _load_intakes(self):
        directory = self.state_dir / "intakes"
        if not directory.exists():
            return
        metadata = {path.stem: path for path in directory.glob("*.json")}
        originals = {path.stem: path for path in directory.iterdir() if path.is_file() and path.suffix not in {".json", ".uploading", ".recording"}}
        if set(metadata) != set(originals) or list(directory.glob("*.uploading")) or list(directory.glob("*.recording")):
            raise ValueError("Incoming review recovery required: original and review records do not match")
        for digest, meta_path in metadata.items():
            record = json.loads(meta_path.read_text())
            record_hash = record.pop("record_sha256", None)
            path = originals[digest]
            data = path.read_bytes()
            expected_record_hash = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if record_hash != expected_record_hash or hashlib.sha256(data).hexdigest() != digest or record.get("incoming", {}).get("sha256") != digest:
                raise ValueError("Incoming review recovery required: source identity mismatch for " + digest)
            filename = record.get("incoming", {}).get("filename", "incoming.docx")
            document = record.get("extracted_document") or extract(data, filename)
            self._validate_extracted_document(data, document, filename)
            self.intakes[digest] = {"document": document, "path": path, "record": record}

    def intake(self, data, filename, selected_reference_id=None, reviewer=None, rationale=None):
        if not isinstance(filename, str) or not filename.lower().endswith(".docx") or len(data) > 2_000_000:
            raise ValueError("Choose one synthetic DOCX under 2 MB")
        document = extract(data, filename)
        return self.intake_extracted(data, document, selected_reference_id, reviewer, rationale)

    def intake_batch(self, files):
        """Run each supplied source through the same automatic intake pipeline."""
        files = list(files)
        if not 1 <= len(files) <= 20:
            raise ValueError("Choose 1 to 20 DOCX files per batch")
        results = []
        counts = {"analysed": 0, "awaiting_reference": 0, "blocked_extraction": 0, "duplicate": 0, "failed": 0}
        for filename, data in files:
            digest = hashlib.sha256(data).hexdigest() if isinstance(data, bytes) else None
            duplicate = digest in self.intakes
            try:
                detail = self.intake(data, filename)
                outcome = "duplicate" if duplicate else ("analysed" if detail["comparison"]["status"] in {"analysed", "complete"} else detail["status"])
                if outcome not in counts:
                    outcome = "awaiting_reference"
                results.append({"filename": filename, "sha256": digest, "id": detail["id"], "outcome": outcome, "family": detail["family"], "reference_id": detail["reference"]["reference_id"], "comparison_status": detail["comparison"]["status"], "reason": detail["reason"]})
            except ValueError as exc:
                outcome = "failed"
                results.append({"filename": filename, "sha256": digest, "outcome": outcome, "reason": str(exc)})
            counts[outcome] += 1
        return {"submitted": len(files), "counts": counts, "items": results}

    def intake_extracted(self, data, document, selected_reference_id=None, reviewer=None, rationale=None):
        document = self._validate_extracted_document(data, document, document.get("filename") if isinstance(document, dict) else None)
        digest = document["sha256"]
        existing = self.intakes.get(digest)
        if existing:
            if hashlib.sha256(existing["path"].read_bytes()).hexdigest() != digest:
                raise ValueError("Stored incoming original is unavailable or changed")
            detail = self.intake_detail(digest)
            if selected_reference_id and detail["reference"]["reference_id"] != selected_reference_id:
                raise ValueError("This original is already bound to a different reference; its review cannot be silently changed")
            return detail

        selected_item = None
        if selected_reference_id:
            selected_item = self.reference_library.get(selected_reference_id)
            if not selected_item or selected_item["metadata"].get("status") != "active" or self._library_source_integrity(selected_item) != "verified":
                raise ValueError("Choose an Active reference with a verified original")
            if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(rationale, str) or not rationale.strip():
                raise ValueError("Name the reviewer and explain why this reference applies")
            if len(reviewer) > 100 or len(rationale) > 2000:
                raise ValueError("Reviewer name or applicability reason is too long")

        if selected_item:
            chosen = {**selected_item["metadata"], "document": selected_item["document"]}
            selection = propose_reference(document, [chosen], eligible_statuses={"active"})
            if selection["status"] not in {"proposed", "proposed_with_gaps"} or selection.get("proposal", {}).get("reference_id") != selected_reference_id:
                raise ValueError("Selected reference does not match the extracted family and applicability context: " + selection["reason"])
        # Reuse the established family-aware #7 proposal and retain its immutable source snapshot.
        matching = self.match_reference_extracted(data, document)
        matching = {key: value for key, value in matching.items() if key != "extracted_document"}
        if selected_item:
            matching = {**matching, "proposal": selection, "selection_mode": "explicit_on_upload"}
        proposal = matching["proposal"]
        family = (proposal.get("context", {}).get("dimensions", {}).get("family", {}) or {}).get("value")
        candidate = proposal.get("proposal") or {}
        comparison = {"status": "not_run", "reason": "A reviewer must establish that the proposed reference applies before comparison."}
        status = "needs_context"
        route = "review_required"
        reason = proposal.get("reason", "Applicability could not be established.")
        analysis = None
        if document["coverage"]["status"] != "complete":
            status, route, reason = "blocked_extraction", "blocked_extraction", "; ".join(document["coverage"]["issues"])
            comparison = {"status": "not_run", "reason": "Extraction is incomplete; comparison was not performed."}
        elif proposal.get("status") in {"proposed", "proposed_with_gaps"} and family == "customer_order":
            library_item = self.reference_library.get(candidate.get("reference_id"))
            if library_item and library_item["metadata"].get("status") == "active" and self._library_source_integrity(library_item) == "verified" and library_item["metadata"]["sha256"] == candidate.get("sha256"):
                reference_record = {**library_item["metadata"], "document": library_item["document"]}
                report = CustomerOrderPack().compare(reference_record, document)
                if report["checks"]["comparison"] == "complete":
                    comparison = {"status": "complete", "method": "deterministic section and text comparison", "reference_id": candidate["reference_id"], "reference_sha256": candidate["sha256"], "observations": [CustomerOrderReview._observation(finding) for finding in report["findings"]], "reason": report["reason"], "route": report["route"], "limitations": report.get("assurance", {}).get("limitations", []), "provisional": True, "human_decision_required": True, "approved": False}
                    status, route, reason = "analysed_needs_review", "review_required", "Chug selected a context-compatible customer-order reference and compared it on upload. Check the proposed reference and findings before deciding."
                else:
                    status, route, reason = "awaiting_reference", "review_required", "The proposed customer-order comparison did not complete; review the reference and source."
            else:
                status, route, reason = "awaiting_reference", "review_required", "The proposed customer-order reference is not Active or its original could not be verified."
        elif proposal.get("status") in {"proposed", "proposed_with_gaps"} and family == "nda" and candidate.get("sha256") in self.references:
            library_item = self.reference_library.get(candidate.get("reference_id"))
            if library_item and library_item["kind"] == "uploaded_synthetic" and library_item["metadata"].get("status") == "active" and self._library_source_integrity(library_item) == "verified":
                reference = self.references[candidate["sha256"]]["document"]
                comparison_report = self.pack.analyse(reference, document, {}, {}, [], self.reference)
                analysis = comparison_report
                comparison = {"status": "analysed", "method": "deterministic NDA comparison", "reference_id": candidate["reference_id"], "reference_sha256": candidate["sha256"], "findings": comparison_report["findings"], "route": comparison_report["route"], "reason": comparison_report["reason"], "limitations": comparison_report["assurance"].get("limitations", []), "provisional": True, "human_decision_required": True, "approved": False}
                status, route, reason = "analysed_needs_review", "review_required", "Chug selected a context-compatible NDA reference and compared it on upload. Check the proposed reference and findings before deciding."
            else:
                status, route = "awaiting_reference", "review_required"
                reason = "The proposed NDA reference is not an active, integrity-verified local standard; comparison was not run."
        elif proposal.get("status") in {"ambiguous_match", "ambiguous_context", "no_suitable_match", "needs_context", "blocked_extraction"}:
            status, route = ("blocked_extraction", "blocked_extraction") if proposal.get("status") == "blocked_extraction" else ("awaiting_reference", "review_required")
            reason = proposal.get("reason", reason)

        record = {
            "incoming": {"filename": document["filename"], "sha256": digest},
            "extracted_document": document,
            "family": family,
            "extraction": document["coverage"],
            "matching": matching,
            "reference": {"status": "proposed" if candidate else "unresolved", "reference_id": candidate.get("reference_id"), "sha256": candidate.get("sha256"), "display_name": candidate.get("display_name")},
            "comparison": comparison,
            "analysis": analysis,
            "status": status, "route": route, "reason": reason,
            "human_decision": {"status": "pending", "required": True, "outcome": None},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        directory = self.state_dir / "intakes"
        directory.mkdir(parents=True, exist_ok=True)
        suffix = Path(document["filename"]).suffix.lower() or ".source"
        original = directory / (digest + suffix)
        temporary = directory / (digest + ".uploading")
        with temporary.open("xb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, original)
        meta = directory / (digest + ".json")
        temporary = directory / (digest + ".recording")
        with temporary.open("x") as handle:
            stored_record = {**record, "record_sha256": hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
            json.dump(stored_record, handle, ensure_ascii=False); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, meta)
        self.intakes[digest] = {"document": document, "path": original, "record": record}
        if selected_item:
            return self.confirm_intake_reference(digest, selected_reference_id, selected_item["metadata"]["sha256"], reviewer, rationale)
        return self.intake_detail(digest)

    def intake_detail(self, digest):
        item = self.intakes.get(digest)
        if not item:
            raise KeyError("Incoming review not found")
        if hashlib.sha256(item["path"].read_bytes()).hexdigest() != digest:
            raise ValueError("Incoming original identity changed; review is withheld")
        record = dict(item["record"])
        record.pop("extracted_document", None)
        confirmations = self.intake_confirmations.all(digest)
        if len(confirmations) > 1:
            raise ValueError("Incoming review has more than one reference confirmation event")
        confirmation = confirmations[0] if confirmations else None
        if confirmation:
            record["reference_confirmation"] = {"status": "confirmed", "reference_id": confirmation["reference_id"], "sha256": confirmation["reference_sha256"], "reviewer": confirmation["reviewer"], "rationale": confirmation["rationale"], "timestamp": confirmation["timestamp"]}
            record["comparison"] = confirmation["comparison"]
            record["analysis"] = confirmation.get("analysis")
            record["status"] = "analysed_needs_review"
            record["route"] = "review_required"
            record["reason"] = "Reference applicability was confirmed by a reviewer; comparison is available for human review."
        reference_sha256 = record.get("reference_confirmation", {}).get("sha256") or record.get("reference", {}).get("sha256")
        reference_id = record.get("reference_confirmation", {}).get("reference_id") or record.get("reference", {}).get("reference_id")
        reference_integrity = "not_linked"
        if reference_id and reference_id in self.reference_library:
            reference_integrity = self._library_source_integrity(self.reference_library[reference_id])
        elif reference_sha256 and reference_sha256 in self.references:
            reference_item = self.references[reference_sha256]
            try:
                reference_integrity = "verified" if hashlib.sha256(reference_item["path"].read_bytes()).hexdigest() == reference_sha256 else "mismatch"
            except OSError:
                reference_integrity = "unavailable"
        review = self._review_records(digest, reference_sha256)
        decisions = review["decisions"]
        record["human_decision"] = {
            "status": "recorded" if review["latest_decision"] else "pending",
            "required": True, "outcome": review["latest_decision"]["decision"] if review["latest_decision"] else None,
            "events": len(decisions), "history": decisions, "last_decision": review["latest_decision"]}
        record["review_state"] = review["review_state"]
        record["latest_flag"] = review["latest_flag"]
        record["contract_actions"] = review["contract_actions"]
        case_id = "I-" + digest[:10]
        assessments = self.finding_assessments.all(case_id)
        latest_assessments = {}
        for assessment in assessments:
            latest_assessments[assessment["finding_id"]] = assessment
        reference_document = self.reference_library[reference_id]["document"] if reference_integrity == "verified" and reference_id in self.reference_library else None
        return {**record, "id": case_id, "document": item["document"], "reference_document": reference_document, "source_integrity": {"incoming": "verified", "reference": reference_integrity}, "original_url": "/api/intakes/" + digest + "/original", "finding_assessments": assessments, "latest_finding_assessments": latest_assessments}

    def confirm_intake_reference(self, digest, reference_id, reference_sha256, reviewer, rationale):
        detail = self.intake_detail(digest)
        if detail.get("reference_confirmation", {}).get("status") == "confirmed":
            raise ValueError("Reference applicability has already been confirmed for this intake")
        proposal = detail.get("matching", {}).get("proposal", {})
        candidate = proposal.get("proposal") or {}
        if proposal.get("status") not in {"proposed", "proposed_with_gaps"} or candidate.get("reference_id") != reference_id or candidate.get("sha256") != reference_sha256:
            raise ValueError("Confirm only the exact reference ID and hash proposed for this incoming document")
        library_item = self.reference_library.get(reference_id)
        if not library_item or library_item["metadata"].get("sha256") != reference_sha256 or library_item["metadata"].get("status") != "active" or self._library_source_integrity(library_item) != "verified":
            raise ValueError("Proposed reference is no longer active or its source integrity cannot be verified")
        if library_item["metadata"].get("family") != detail.get("family"):
            raise ValueError("Proposed reference family does not match the incoming document")
        stamp = datetime.now(timezone.utc).isoformat()
        confirmation = {"confirmed": True, "reference_id": reference_id, "sha256": reference_sha256, "reviewer": reviewer, "rationale": rationale, "timestamp": stamp}
        analysis = None
        if detail["family"] == "customer_order":
            reference_record = {**library_item["metadata"], "document": library_item["document"]}
            report = CustomerOrderPack().compare(reference_record, detail["document"])
            if report["checks"]["comparison"] != "complete":
                raise ValueError("Customer-order comparison did not complete")
            observations = [CustomerOrderReview._observation(finding) for finding in report["findings"]]
            comparison = {"status": "complete", "method": "deterministic section and text comparison", "baseline": report["baseline"], "observations": observations, "reason": report["reason"], "route": report["route"], "limitations": report.get("assurance", {}).get("limitations", []), "human_decision_required": True, "approved": False}
        elif detail["family"] == "nda":
            reference = self.references.get(reference_sha256)
            if not reference:
                raise ValueError("NDA comparison reference is unavailable")
            analysis = self.pack.analyse(reference["document"], detail["document"], {}, {}, [], self.reference)
            comparison = {"status": "analysed", "method": "deterministic NDA comparison", "reference_id": reference_id, "reference_sha256": reference_sha256, "findings": analysis["findings"], "route": analysis["route"], "reason": analysis["reason"], "limitations": analysis["assurance"].get("limitations", []), "human_decision_required": True, "approved": False}
        else:
            raise ValueError("No comparison engine is available for this incoming family")
        event = self.intake_confirmations.append(digest, detail["incoming"]["filename"], reference_id, reference_sha256, reviewer, rationale, comparison, analysis)
        return self.intake_detail(digest)

    def record_intake_decision(self, digest, reviewer, decision, rationale, conditions="", finding_ids=None, independent_original_reviewed=False, contract_action=None, unresolved_findings_acknowledged=False):
        detail = self.intake_detail(digest)
        if decision == "approve" and independent_original_reviewed is not True:
            raise ValueError("Before recording approval, confirm that you independently reviewed the exact incoming original document")
        findings = list((detail.get("analysis") or {}).get("findings", [])) or list(detail.get("comparison", {}).get("findings", []))
        observations = detail.get("comparison", {}).get("observations", [])
        findings.extend(observations)
        if decision == "approve":
            unresolved = [finding for finding in findings if
                          detail["latest_finding_assessments"].get(finding.get("id"), {}).get("assessment")
                          not in {"not_relevant", "acceptable"}]
            if unresolved and (unresolved_findings_acknowledged is not True or
                               not isinstance(rationale, str) or len(rationale.strip()) < 20):
                raise ValueError("Acknowledge unresolved findings and explain acceptance before approval")
        by_id = {row.get("id"): row for row in findings}
        finding_ids = finding_ids or []
        if not isinstance(finding_ids, list) or any(item not in by_id for item in finding_ids):
            raise ValueError("Choose only findings belonging to this incoming review")
        sources = []
        for finding_id in finding_ids:
            finding = by_id[finding_id]
            incoming = finding.get("sources", finding.get("incoming_passages", []))
            for passage in incoming:
                sources.append({"finding_id": finding_id, "anchor": passage["anchor"], "text": passage["text"]})
        reference_sha256 = detail.get("reference_confirmation", {}).get("sha256") or detail.get("reference", {}).get("sha256")
        return self.ledger.append(digest, detail["incoming"]["filename"], reviewer, decision, rationale, finding_ids, conditions, sources, reference_sha256, independent_original_reviewed, contract_action, unresolved_findings_acknowledged)

    def _review_records(self, sha256, reference_sha256, *, legacy=False):
        """Preserve historical ledger bytes while treating earlier mislabeled flags as pending."""
        default_reference = self.bundled_reference_sha256 if legacy else None
        events = [event for event in self.ledger.all(sha256)
                  if event.get("reference_sha256", default_reference) == reference_sha256]
        decisions = [event for event in events if event.get("contract_action") != "flag_for_review"]
        flagged = [event for event in events if event.get("contract_action") == "flag_for_review"]
        flagged.extend(event for event in self.review_flags.all(sha256)
                       if event.get("reference_sha256") == reference_sha256)
        flags = sorted(flagged, key=lambda event: event["timestamp"])
        actions = sorted([event for event in decisions if event.get("contract_action")] + flags,
                         key=lambda event: event["timestamp"])
        last_decision = decisions[-1] if decisions else None
        last_flag = flags[-1] if flags else None
        pending_flag = bool(last_flag and (not last_decision or last_flag["timestamp"] > last_decision["timestamp"]))
        return {"decisions": decisions, "contract_actions": actions,
                "latest_decision": None if pending_flag else last_decision,
                "latest_flag": last_flag if pending_flag else None,
                "review_state": "flagged" if pending_flag else "decided" if last_decision else "pending"}

    def queue(self):
        rows = []
        for document_id, item in self.contracts.items():
            document = item["document"]
            review = self.analysis(document_id)
            human = self._review_records(document["sha256"], item["reference_sha256"], legacy=True)
            rows.append({"id": document_id, "filename": document["filename"], "display_name": self.pack.display_name(document), "sha256": document["sha256"], "reference_sha256": item["reference_sha256"], "route": review["route"], "reason": review["reason"], "findings_count": len(review["findings"]), "latest_decision": human["latest_decision"], "latest_flag": human["latest_flag"], "review_state": human["review_state"]})
        for digest, item in self.intakes.items():
            detail = self.intake_detail(digest)
            record = detail
            if record["status"] == "analysed_needs_review" and record.get("analysis") is not None:
                findings_count = len(record["analysis"].get("findings", []))
            else:
                findings_count = len(record.get("comparison", {}).get("findings", record.get("comparison", {}).get("observations", [])))
            reference_sha256 = record.get("reference_confirmation", {}).get("sha256") or record.get("reference", {}).get("sha256")
            rows.append({"id": "I-" + digest[:10], "intake_sha256": digest, "filename": item["document"]["filename"], "display_name": Path(item["document"]["filename"]).stem, "sha256": digest, "reference_sha256": reference_sha256, "route": record["route"], "reason": record["reason"], "findings_count": findings_count, "latest_decision": record.get("human_decision", {}).get("last_decision"), "latest_flag": record["latest_flag"], "review_state": record["review_state"], "intake": True, "status": record["status"]})
        return sorted(rows, key=lambda row: (-self.pack.route_order[row["route"]], row["id"]))

    def match_reference(self, data, filename):
        if not isinstance(filename, str) or not filename.lower().endswith(".docx") or len(data) > 2_000_000:
            raise ValueError("Choose one synthetic DOCX under 2 MB")
        document = extract(data, filename)
        return self.match_reference_extracted(data, document)

    def match_reference_extracted(self, data, document):
        document = self._validate_extracted_document(data, document, document.get("filename") if isinstance(document, dict) else None)
        filename = document["filename"]
        digest = document["sha256"]
        existing = self.match_intakes.get(digest)
        if existing:
            if hashlib.sha256(existing["path"].read_bytes()).hexdigest() != digest:
                raise ValueError("Stored incoming original is unavailable or changed")
            return existing["record"]
        references, unavailable = self._matching_references()
        proposal = propose_reference(document, references, eligible_statuses={"active"})
        proposal["excluded"].extend(unavailable)
        record = {
            "incoming": {"filename": document["filename"], "sha256": digest},
            "extracted_document": document,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "proposal": proposal,
            "binding": None,
            "human_decision": {"status": "pending", "required": True},
            "comparison": {"status": "not_run"},
        }
        directory = self.state_dir / "reference_matches"
        directory.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix.lower() or ".source"
        original = directory / (digest + suffix)
        meta_path = directory / (digest + ".json")
        temporary = directory / (digest + ".uploading")
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, original)
        temporary = directory / (digest + ".recording")
        with temporary.open("x") as handle:
            stored = {**record, "sha256": digest, "record_sha256": hashlib.sha256(json.dumps({**record, "sha256": digest}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
            json.dump(stored, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, meta_path)
        self.match_intakes[digest] = {"document": document, "path": original, "record": record}
        return record

    def reference_match_detail(self, digest):
        item = self.match_intakes.get(digest)
        if not item:
            raise KeyError("Reference match not found")
        try:
            intact = hashlib.sha256(item["path"].read_bytes()).hexdigest() == digest
        except OSError:
            intact = False
        if not intact:
            raise ValueError("Incoming original is unavailable or changed; proposal is withheld")
        return {**item["record"], "original_url": "/api/reference-matches/" + digest + "/original"}

    def update_reference_status(self, reference_id, status, reason):
        if status not in {"superseded", "withdrawn"}:
            raise ValueError("Reference status must be Superseded or Withdrawn")
        item = self.reference_library.get(reference_id)
        if not item or item["kind"] != "uploaded_synthetic":
            raise ValueError("Only locally uploaded synthetic standards can change status")
        if self._library_source_integrity(item) != "verified":
            raise ValueError("Reference original is unavailable or changed")
        if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000:
            raise ValueError("Provide a reason of 1 to 1000 characters")
        meta_path = item["path"].with_suffix(".json")
        stored = json.loads(meta_path.read_text())
        record_hash = stored.pop("record_sha256", None)
        expected = hashlib.sha256(json.dumps(stored, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if record_hash != expected:
            raise ValueError("Reference metadata integrity mismatch; status change is blocked")
        current = item["metadata"].get("status")
        if current != "active":
            raise ValueError("Only Active standards can be superseded or withdrawn")
        history = list(item["metadata"].get("status_history", []))
        history.append({"from": current, "to": status, "reason": reason.strip(), "timestamp": datetime.now(timezone.utc).isoformat()})
        stored["status"] = status
        stored.pop("approval_status", None)
        stored["status_history"] = history
        stored["record_sha256"] = hashlib.sha256(json.dumps(stored, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        temporary = meta_path.with_suffix(".recording")
        with temporary.open("x") as handle:
            json.dump(stored, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, meta_path)
        item["metadata"].update({"status": status, "status_history": history})
        if item["metadata"].get("sha256") == self.active_reference_sha256:
            self.select_reference(self.bundled_reference_sha256)
        return {**item["metadata"], "kind": item["kind"], "source_integrity": "verified"}

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
        available = []
        for sha, item in self.references.items():
            library_item = next((row for row in self.reference_library.values() if row["metadata"].get("sha256") == sha), None)
            if library_item and library_item["metadata"].get("status") in {"superseded", "withdrawn"}:
                continue
            available.append({"sha256": sha, "filename": item["document"]["filename"], "kind": item["kind"], "family": item.get("family", "nda")})
        return {"current": {**current["document"], "kind": current["kind"], "source_integrity": "verified" if intact else "mismatch"}, "available": available}

    def _library_source_integrity(self, item):
        try:
            return "verified" if hashlib.sha256(item["path"].read_bytes()).hexdigest() == item["metadata"]["sha256"] else "mismatch"
        except OSError:
            return "unavailable"

    def reference_library_list(self):
        rows = []
        for item in self.reference_library.values():
            rows.append({**item["metadata"], "kind": item["kind"], "source_integrity": self._library_source_integrity(item), "original_url": "/api/reference-library/" + item["metadata"]["reference_id"] + "/original"})
        return {"references": rows, "count": len(rows)}

    def reference_library_detail(self, reference_id):
        item = self.reference_library.get(reference_id)
        if not item:
            raise KeyError("Reference not found")
        integrity = self._library_source_integrity(item)
        if integrity != "verified":
            raise ValueError("Reference original is " + integrity + "; source content is withheld")
        return {**item["metadata"], "kind": item["kind"], "source_integrity": integrity, "original_url": "/api/reference-library/" + reference_id + "/original", "document": item["document"]}

    def select_reference(self, digest):
        if digest not in self.references or self.references[digest].get("family", "nda") != "nda":
            raise ValueError("Reference not found")
        library_item = next((item for item in self.reference_library.values() if item["metadata"].get("sha256") == digest), None)
        if library_item and library_item["metadata"].get("status") in {"superseded", "withdrawn"}:
            raise ValueError("Superseded or Withdrawn references cannot be selected for new NDA uploads")
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
        display_name = Path(filename).stem
        version = "1.0"
        classification = uploaded_reference_metadata(document, display_name, version)
        if classification["family"] == "nda":
            self._validate_reference(document)
        digest = document["sha256"]
        # Research specimens are visible examples, not controlled registrations.
        # A deliberate upload of the same bytes creates a separate Active record.
        existing = next((item for item in self.reference_library.values() if item["metadata"]["sha256"] == digest and item["kind"] == "uploaded_synthetic"), None)
        if existing:
            if self._library_source_integrity(existing) != "verified":
                raise ValueError("Stored reference original is unavailable or changed; upload is blocked")
            result = self.reference_info()
            result["library_item"] = {**existing["metadata"], "kind": existing["kind"], "source_integrity": self._library_source_integrity(existing), "original_url": "/api/reference-library/" + existing["metadata"]["reference_id"] + "/original"}
            if classification["family"] == "nda" and digest in self.references:
                return self.select_reference(digest) | {"library_item": result["library_item"]}
            return result
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
            stored_metadata = uploaded_reference_metadata(document, Path(filename).stem, "1.0")
            stored_metadata = {**stored_metadata, "sha256": digest, "filename": document["filename"], "kind": "uploaded_synthetic"}
            stored_metadata["record_sha256"] = hashlib.sha256(json.dumps(stored_metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            json.dump(stored_metadata, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, metadata)
        stored_metadata = json.loads(metadata.read_text())
        library_item = {"metadata": stored_metadata, "document": document, "path": original, "kind": "uploaded_synthetic"}
        self.reference_library[stored_metadata["reference_id"]] = library_item
        if stored_metadata["family"] == "nda":
            self.references[digest] = {"document": document, "path": original, "kind": "uploaded_synthetic", "family": "nda"}
            result = self.select_reference(digest)
        else:
            result = self.reference_info()
        result["library_item"] = {**stored_metadata, "kind": "uploaded_synthetic", "source_integrity": self._library_source_integrity(library_item), "original_url": "/api/reference-library/" + stored_metadata["reference_id"] + "/original"}
        return result

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

    def detail(self, document_id):
        item = self.contracts[document_id]
        document = item["document"]
        reference_sha256 = item["reference_sha256"]
        review_records = self._review_records(document["sha256"], reference_sha256, legacy=True)
        history = review_records["decisions"]
        knowledge_events = self.knowledge.all()
        publications = []
        for event in knowledge_events:
            if event["type"] != "publish" or event["sha256"] != document["sha256"] or event.get("reference_sha256", self.bundled_reference_sha256) != reference_sha256:
                continue
            withdrawal = next((row for row in knowledge_events if row["type"] == "withdraw" and row["publication_id"] == event["id"]), None)
            publications.append({**event, "status": "withdrawn" if withdrawal else "active", "withdrawal": withdrawal})
        analysis = self.analysis(document_id)
        assessment_events = self.finding_assessments.all(document_id)
        latest_assessments = {}
        for assessment in assessment_events:
            latest_assessments[assessment["finding_id"]] = assessment
        analysis["assurance"]["human_review"] = {"status": "recorded" if review_records["latest_decision"] else "not recorded", "last_decision": review_records["latest_decision"]["decision"] if review_records["latest_decision"] else None, "events": len(history)}
        contract_actions = review_records["contract_actions"]
        analysis["assessments"] = latest_assessments
        analysis["contract_actions"] = contract_actions
        return {"id": document_id, "display_name": self.pack.display_name(document), "document": document, "reference": self.references[reference_sha256]["document"], "reference_kind": self.references[reference_sha256]["kind"], "analysis": analysis, "history": history, "finding_assessments": assessment_events, "latest_finding_assessments": latest_assessments, "contract_actions": contract_actions, "review_state": review_records["review_state"], "latest_flag": review_records["latest_flag"], "publications": publications, "corrections": self.correction_history(document_id), "ai": self.ai.status(), "ai_results": self.ai_results.get((document["sha256"], reference_sha256), [])}

    def assess_finding(self, document_id, finding_id, assessment, reviewer, reason):
        if document_id in self.contracts:
            detail = self.detail(document_id)
            rows = detail["analysis"]["findings"]
            reference = detail["reference"]
            source_hash = detail["document"]["sha256"]
        else:
            digest = next((key for key in self.intakes if document_id == "I-" + key[:10]), None)
            if not digest:
                raise KeyError("Review case not found")
            detail = self.intake_detail(digest)
            if detail["source_integrity"]["incoming"] != "verified" or detail["source_integrity"]["reference"] != "verified":
                raise ValueError("Incoming or reference original is not verified; assessment is unavailable")
            rows = list((detail.get("analysis") or {}).get("findings", [])) or list(detail.get("comparison", {}).get("findings", [])) or list(detail.get("comparison", {}).get("observations", []))
            reference = {"reference_id": detail.get("reference_confirmation", {}).get("reference_id") or detail.get("reference", {}).get("reference_id"), "sha256": detail.get("reference_confirmation", {}).get("sha256") or detail.get("reference", {}).get("sha256")}
            source_hash = digest
        finding = next((row for row in rows if row.get("id") == finding_id), None)
        if not finding:
            raise ValueError("Unknown finding reference")
        passages = finding.get("sources", finding.get("incoming_passages", []))
        ref_evidence = finding.get("reference_passages") or finding.get("reference") or finding.get("baseline") or finding.get("reference_passage")
        if not passages and not ref_evidence:
            raise ValueError("This observation has no source passages to assess")
        evidence = {"title": finding.get("title") or finding.get("summary", "Observed difference"),
                    "explanation": finding.get("explanation") or finding.get("reason", ""),
                    "sources": passages, "reference": ref_evidence}
        ref = reference
        return self.finding_assessments.append(case_id=document_id, finding_id=finding_id,
            assessment=assessment, reviewer=reviewer, reason=reason,
            source_sha256=source_hash, reference_id=ref.get("reference_id") or ref.get("filename"), reference_sha256=ref["sha256"], evidence=evidence)

    def record_contract_action(self, document_id, action, reviewer, rationale,
                               independent_original_reviewed=False, unresolved_findings_acknowledged=False):
        if action not in {"accept_contract", "flag_for_review"}:
            raise ValueError("Choose Accept contract or Flag for further review")
        if document_id in self.contracts:
            detail = self.detail(document_id)
            source_sha256 = detail["document"]["sha256"]
            filename = detail["document"]["filename"]
            reference_sha256 = detail["reference"]["sha256"]
            findings = detail["analysis"]["findings"]
        else:
            digest = next((key for key in self.intakes if document_id == "I-" + key[:10]), None)
            if not digest:
                raise KeyError("Review case not found")
            detail = self.intake_detail(digest)
            source_sha256 = digest
            filename = detail["incoming"]["filename"]
            reference_sha256 = detail.get("reference_confirmation", {}).get("sha256") or detail.get("reference", {}).get("sha256")
            findings = (detail.get("analysis") or {}).get("findings") or detail.get("comparison", {}).get("findings") or detail.get("comparison", {}).get("observations", [])
        if action == "flag_for_review":
            prior = self._review_records(source_sha256, reference_sha256, legacy=document_id in self.contracts)
            return self.review_flags.append(sha256=source_sha256, filename=filename, reviewer=reviewer,
                                            rationale=rationale, reference_sha256=reference_sha256,
                                            reuse_last_if_same=prior["review_state"] == "flagged")
        if independent_original_reviewed is not True:
            raise ValueError("Before accepting, confirm that you independently reviewed the exact incoming original document")
        assessments = detail.get("latest_finding_assessments", {})
        unresolved = [row for row in findings
                      if assessments.get(row.get("id"), {}).get("assessment") not in {"not_relevant", "acceptable"}]
        if unresolved:
            if unresolved_findings_acknowledged is not True:
                raise ValueError("Acknowledge each unresolved or unassessed finding before accepting")
            if not isinstance(rationale, str) or len(rationale.strip()) < 20:
                raise ValueError("Explain why you accept despite unresolved or unassessed findings")
        if document_id not in self.contracts:
            return self.record_intake_decision(digest, reviewer, "approve", rationale,
                finding_ids=[], independent_original_reviewed=True, contract_action="accept_contract",
                unresolved_findings_acknowledged=unresolved_findings_acknowledged)
        return self.ledger.append(source_sha256, filename, reviewer, "approve", rationale, [],
                                  reference_sha256=reference_sha256, independent_original_reviewed=True,
                                  contract_action="accept_contract",
                                  unresolved_findings_acknowledged=unresolved_findings_acknowledged)

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

    def _multipart_docx(self, with_fields=False):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data;"):
            raise ValueError("Choose a DOCX file")
        data = self._body()
        message = BytesParser(policy=policy.default).parsebytes(b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode() + b"\r\n\r\n" + data)
        parts = list(message.iter_parts()) if message.is_multipart() else []
        files = [part for part in parts if part.get_param("name", header="content-disposition") == "file"]
        if len(files) != 1:
            raise ValueError("Choose one DOCX file")
        filename = files[0].get_filename() or "uploaded.docx"
        if not filename.lower().endswith(".docx"):
            raise ValueError("DOCX only")
        if with_fields:
            fields = {}
            for part in parts:
                name = part.get_param("name", header="content-disposition")
                if name != "file":
                    if name in fields or name not in {"reference_id", "reviewer", "rationale"}:
                        raise ValueError("Unknown or repeated upload field")
                    fields[name] = part.get_content()
            return files[0].get_payload(decode=True), filename, fields
        return files[0].get_payload(decode=True), filename

    def _multipart_batch(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data;"):
            raise ValueError("Choose a DOCX batch")
        data = self._body(42_000_000)
        message = BytesParser(policy=policy.default).parsebytes(b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode() + b"\r\n\r\n" + data)
        parts = list(message.iter_parts()) if message.is_multipart() else []
        if not 1 <= len(parts) <= 20 or any(part.get_param("name", header="content-disposition") != "file" for part in parts):
            raise ValueError("Choose 1 to 20 DOCX files per batch")
        return [(part.get_filename() or "uploaded.docx", part.get_payload(decode=True)) for part in parts]

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/queue":
            try:
                return self._json({"items": self.app.queue()})
            except ValueError as exc:
                return self._error(409, str(exc))
        intake_detail = re.fullmatch(r"/api/intakes/([0-9a-f]{64})(/original)?", path)
        if intake_detail:
            try:
                item = self.app.intake_detail(intake_detail.group(1))
            except KeyError as exc:
                return self._error(404, str(exc).strip("'"))
            except (OSError, ValueError) as exc:
                return self._error(409, str(exc))
            if intake_detail.group(2):
                data = self.app.intakes[intake_detail.group(1)]["path"].read_bytes()
                self.send_response(200)
                filename = self.app.intakes[intake_detail.group(1)]["document"]["filename"]
                self.send_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(Path(filename).name))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return self.wfile.write(data)
            return self._json(item)
        if path == "/api/reference":
            return self._json(self.app.reference_info())
        if path == "/api/reference-library":
            try:
                return self._json(self.app.reference_library_list())
            except ValueError as exc:
                return self._error(409, str(exc))
        match_detail = re.fullmatch(r"/api/reference-matches/([0-9a-f]{64})", path)
        if match_detail:
            try:
                return self._json(self.app.reference_match_detail(match_detail.group(1)))
            except KeyError as exc:
                return self._error(404, str(exc).strip("'"))
            except ValueError as exc:
                return self._error(409, str(exc))
        match_original = re.fullmatch(r"/api/reference-matches/([0-9a-f]{64})/original", path)
        if match_original:
            item = self.app.match_intakes.get(match_original.group(1))
            if not item:
                return self._error(404, "Reference match not found")
            try:
                data = item["path"].read_bytes()
            except OSError:
                return self._error(409, "Incoming original unavailable")
            if hashlib.sha256(data).hexdigest() != match_original.group(1):
                return self._error(409, "Incoming original identity changed")
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.send_header("Content-Disposition", 'attachment; filename="incoming-standard-match.docx"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return self.wfile.write(data)
        library_item = re.fullmatch(r"/api/reference-library/([A-Za-z0-9_-]+)", path)
        if library_item:
            try:
                return self._json(self.app.reference_library_detail(library_item.group(1)))
            except KeyError as exc:
                return self._error(404, str(exc).strip("'"))
            except ValueError as exc:
                return self._error(409, str(exc))
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
        library_original = re.fullmatch(r"/api/reference-library/([A-Za-z0-9_-]+)/original", path)
        if library_original:
            item = self.app.reference_library.get(library_original.group(1))
            if not item:
                return self._error(404, "Reference not found")
            try:
                data = item["path"].read_bytes()
            except OSError:
                return self._error(409, "Reference original unavailable")
            if hashlib.sha256(data).hexdigest() != item["metadata"]["sha256"]:
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
        path = urlparse(self.path).path
        try:
            if path == "/api/upload":
                data, filename = self._multipart_docx()
                return self._json({"id": self.app.upload(data, filename)}, 201)
            if path == "/api/intakes":
                data, filename, fields = self._multipart_docx(with_fields=True)
                return self._json(self.app.intake(data, filename, fields.get("reference_id"), fields.get("reviewer"), fields.get("rationale")), 201)
            if path == "/api/intakes/batch":
                return self._json(self.app.intake_batch(self._multipart_batch()), 201)
            if path == "/api/reference-matches":
                data, filename = self._multipart_docx()
                return self._json(self.app.match_reference(data, filename), 201)
            if path == "/api/reference/upload":
                data, filename = self._multipart_docx()
                return self._json(self.app.upload_reference(data, filename), 201)
            body = json.loads(self._body(100_000))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object")
            if path == "/api/finding-assessments":
                document_id = body.get("document_id")
                if not isinstance(document_id, str):
                    raise ValueError("Invalid contract ID")
                event = self.app.assess_finding(document_id, body.get("finding_id"),
                    body.get("assessment"), body.get("reviewer", ""), body.get("reason", ""))
                return self._json(event, 201)
            if path == "/api/contract-actions":
                document_id = body.get("document_id")
                if not isinstance(document_id, str):
                    raise ValueError("Invalid contract ID")
                event = self.app.record_contract_action(document_id, body.get("action"),
                    body.get("reviewer", ""), body.get("rationale", ""),
                    body.get("independent_original_reviewed", False),
                    body.get("unresolved_findings_acknowledged", False))
                return self._json(event, 201)
            reference_confirmation = re.fullmatch(r"/api/intakes/([0-9a-f]{64})/reference-confirmation", path)
            if reference_confirmation:
                return self._json(self.app.confirm_intake_reference(reference_confirmation.group(1), body.get("reference_id"), body.get("reference_sha256"), body.get("reviewer", ""), body.get("rationale", "")), 201)
            intake_decision = re.fullmatch(r"/api/intakes/([0-9a-f]{64})/decisions", path)
            if intake_decision:
                return self._json(self.app.record_intake_decision(intake_decision.group(1), body.get("reviewer", ""), body.get("decision", ""), body.get("rationale", ""), body.get("conditions", ""), body.get("finding_ids", []), body.get("independent_original_reviewed", False)), 201)
            if path == "/api/reference/select":
                return self._json(self.app.select_reference(body.get("sha256")))
            reference_status = re.fullmatch(r"/api/reference-library/([A-Za-z0-9_-]+)/status", path)
            if reference_status:
                return self._json(self.app.update_reference_status(reference_status.group(1), body.get("status"), body.get("reason", "")), 201)
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
                if body.get("decision") == "approve":
                    if body.get("independent_original_reviewed") is not True:
                        raise ValueError("Confirm independent review of the original before approval")
                    unresolved = [finding for finding in detail["analysis"]["findings"]
                                  if detail["latest_finding_assessments"].get(finding["id"], {}).get("assessment")
                                  not in {"not_relevant", "acceptable"}]
                    if unresolved and (body.get("unresolved_findings_acknowledged") is not True or
                                       not isinstance(body.get("rationale"), str) or len(body["rationale"].strip()) < 20):
                        raise ValueError("Acknowledge unresolved findings and explain acceptance")
                event = self.app.ledger.append(doc["sha256"], doc["filename"], body.get("reviewer", ""), body.get("decision", ""), body.get("rationale", ""), finding_ids, body.get("conditions", ""), considered_sources, detail["reference"]["sha256"], independent_original_reviewed=body.get("independent_original_reviewed") is True, unresolved_findings_acknowledged=body.get("unresolved_findings_acknowledged") is True)
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


def default_state_dir(workspace: Path | None = None) -> Path:
    """Preserve existing local decisions when the default folder name changes."""
    root = Path.cwd() if workspace is None else workspace
    current = root / ".chug-data"
    legacy = root / ".chugchug-data"  # Previous name, supported for migration only.
    if legacy.is_dir() and not current.exists():
        shutil.copytree(legacy, current)
        print("Existing review state copied to .chug-data (original retained as backup).", flush=True)
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-dir", type=Path, default=None)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    state_dir = args.state_dir if args.state_dir is not None else default_state_dir()
    Handler.app = App(root, state_dir.resolve())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("Chug synthetic review: http://127.0.0.1:%d" % args.port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
