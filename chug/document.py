"""Conservative DOCX extraction with stable, inspectable source anchors."""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REQUIRED_PART = "word/document.xml"
UNSUPPORTED = {"drawing", "pict", "object", "altChunk", "sdt", "fldChar", "fldSimple", "instrText", "del", "ins", "txbxContent", "footnoteReference", "endnoteReference", "commentReference", "vanish", "webHidden", "specVanish", "strike", "dstrike"}
UNSUPPORTED_PARTS = ("word/footnotes", "word/endnotes", "word/comments", "word/embeddings/", "word/media/", "word/charts/", "word/diagrams/")
METADATA_PARTS = {"word/styles.xml", "word/stylesWithEffects.xml", "word/settings.xml", "word/webSettings.xml", "word/fontTable.xml", "word/numbering.xml"}
MAX_SOURCE_BYTES = 2_000_000
MAX_PDF_PAGES = 100
MAX_PDF_TEXT_CHARS = 1_000_000
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def source_format(data: bytes) -> str | None:
    """Identify the received container from its bytes, never browser MIME."""
    if b"%PDF-" in data[:1024]:
        return "pdf"
    if data.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if REQUIRED_PART in archive.namelist():
                    return "docx"
        except (zipfile.BadZipFile, OSError):
            pass
    return None


def source_extension(document: dict) -> str:
    detected = document.get("format")
    if detected in {"docx", "pdf"}:
        return "." + detected
    return Path(document.get("filename", "")).suffix.lower() or ".source"


def media_type_for(document: dict | str) -> str:
    if isinstance(document, dict):
        if document.get("format") == "pdf":
            return PDF_MIME_TYPE
        if document.get("format") == "docx":
            return DOCX_MIME_TYPE
        filename = document.get("filename", "")
    else:
        filename = document
    return PDF_MIME_TYPE if Path(filename).suffix.lower() == ".pdf" else DOCX_MIME_TYPE


def _pdf_unsupported_content(reader, issues, limitations):
    root = reader.trailer.get("/Root", {})
    if root.get("/OpenAction") or root.get("/AA"):
        issues.append("PDF contains an automatic or additional action; active content was not run and manual review is required")
    if root.get("/OCProperties"):
        issues.append("PDF contains optional-content layers whose visibility may change the wording")
    names = root.get("/Names", {})
    if names.get("/JavaScript"):
        issues.append("PDF contains document JavaScript that is not executed and requires manual review")
    if names.get("/EmbeddedFiles"):
        issues.append("PDF contains embedded files that are not extracted")
    if root.get("/AcroForm"):
        fields = reader.get_fields() or {}
        non_signature = [field for field in fields.values() if field.get("/FT") != "/Sig"]
        if non_signature:
            issues.append("PDF contains form fields whose values are not included in the extracted text")
        elif fields:
            limitations.append("A signature field may be present; cryptographic validity and signatory identity are not verified")
    def contains_image(resources, visited=None, depth=0):
        if depth > 10 or not resources:
            return False
        visited = visited or set()
        xobjects = resources.get("/XObject", {})
        for reference in xobjects.values():
            obj = reference.get_object()
            if id(obj) in visited:
                continue
            visited.add(id(obj))
            subtype = obj.get("/Subtype")
            if subtype == "/Image":
                return True
            if subtype == "/Form" and contains_image(obj.get("/Resources", {}), visited, depth + 1):
                return True
        return False

    for page_number, page in enumerate(reader.pages, 1):
        for annotation in page.get("/Annots", []) or []:
            obj = annotation.get_object()
            if obj.get("/Subtype") == "/Widget" and obj.get("/FT") == "/Sig":
                limitations.append(f"Page {page_number} contains a signature widget; signatures are not verified")
            else:
                issues.append(f"Page {page_number} contains annotations or links that are not represented in extracted text")
                break
        resources = page.get("/Resources", {})
        if contains_image(resources):
            issues.append(f"Page {page_number} contains image content that may include stamps, handwriting or omitted wording; OCR/manual review is required")
    return root


def _extract_pdf(data: bytes, filename: str) -> dict:
    result = {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(), "units": [],
              "coverage": {"status": "blocked", "issues": [], "parts": [], "limitations": []}, "size": len(data), "format": "pdf"}
    issues, limitations = result["coverage"]["issues"], result["coverage"]["limitations"]
    try:
        from pypdf import PdfReader, apply_configuration
        with apply_configuration(
            maximum_declared_stream_length=10_000_000,
            array_based_stream_maximum_output_length=10_000_000,
            array_maximum_element_count=10_000,
            dictionary_maximum_element_count=10_000,
            jbig2_maximum_output_length=2_000_000,
            lzw_maximum_output_length=10_000_000,
            run_length_maximum_output_length=10_000_000,
            zlib_maximum_output_length=10_000_000,
            zlib_maximum_recovery_input_length=2_000_000,
            brotli_maximum_output_length=10_000_000,
            image_maximum_buffer_size=2_000_000,
            stream_filters_maximum_length=8,
            stream_decoding_work_maximum_length=40_000_000,
            stream_parsing_work_maximum_count=250_000,
            page_tree_maximum_entries=MAX_PDF_PAGES + 1,
            page_tree_maximum_depth=30,
            form_fields_maximum_entries=1_000,
            form_fields_maximum_depth=30,
            xform_maximum_invocations_per_extraction=1_000,
        ):
            reader = PdfReader(io.BytesIO(data), strict=True, root_object_recovery_limit=10_000)
            return _read_pdf_pages(reader, result, issues, limitations)
    except ImportError:
        issues.append("PDF support requires the pinned pypdf dependency; the original is preserved but extraction is unavailable")
        result["coverage"]["reason"] = "dependency_unavailable"
    except Exception as exc:
        # Parsing failures are intentionally converted to a blocked source record.
        issues.append("Unreadable or malformed PDF: " + str(exc)[:300])
        result["coverage"]["reason"] = "malformed"
    return result


def _read_pdf_pages(reader, result, issues, limitations):
    if reader.is_encrypted:
        issues.append("Password-protected PDFs are not supported; provide an authorised unencrypted copy for manual review")
        result["coverage"]["reason"] = "encrypted"
        return result
    page_count = len(reader.pages)
    result["coverage"]["page_count"] = page_count
    if page_count == 0:
        raise ValueError("PDF has no pages")
    if page_count > MAX_PDF_PAGES:
        issues.append(f"PDF exceeds the {MAX_PDF_PAGES}-page local limit")
        result["coverage"]["reason"] = "too_many_pages"
        return result
    _pdf_unsupported_content(reader, issues, limitations)
    character_count = 0
    for page_number, page in enumerate(reader.pages, 1):
        part = f"pdf:page:{page_number}"
        result["coverage"]["parts"].append(part)
        text = page.extract_text(extraction_mode="layout") or ""
        if not text.strip():
            issues.append(f"Page {page_number} has no extractable text; image-only or otherwise unsupported content requires OCR/manual review")
            result["coverage"]["reason"] = "needs_ocr"
            continue
        character_count += len(text)
        if character_count > MAX_PDF_TEXT_CHARS:
            issues.append(f"Extracted PDF text exceeds the {MAX_PDF_TEXT_CHARS}-character resource limit")
            result["coverage"]["reason"] = "text_limit"
            result["units"].clear()
            return result
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        aligned_lines = [line for line in lines if re.search(r"\S {4,}\S", line)]
        signature_pair = len(aligned_lines) == 1 and re.search(r"\bsigned for .+\s{4,}signed for\b", aligned_lines[0], re.IGNORECASE)
        if any("\t" in line for line in lines) or (aligned_lines and not signature_pair):
            issues.append(f"Page {page_number} has table-like or column-aligned text whose reading order is ambiguous")
        for line_number, line in enumerate(lines, 1):
            value = " ".join(line.split())
            result["units"].append({"anchor": f"pdf:p{page_number}:l{line_number}", "part": "word/document.xml", "kind": "paragraph", "text": value})
    limitations.append("Text extraction does not visually verify vector marks, stamps, handwriting, layout order or the rendered page; inspect the preserved original.")
    limitations.append("Cryptographic signatures and signatory identity are not verified.")
    if not result["units"] and not issues:
        issues.append("PDF has no extractable text")
        result["coverage"]["reason"] = "needs_ocr"
    if not issues:
        result["coverage"]["status"] = "complete"
    return result


def _tag(element):
    return element.tag.rsplit("}", 1)[-1]


def _text(element):
    parts = []
    for node in element.iter():
        kind = _tag(node)
        if kind == "t":
            parts.append(node.text or "")
        elif kind == "tab":
            parts.append("\t")
        elif kind in ("br", "cr"):
            parts.append("\n")
    return "".join(parts).strip()


def _nonliteral_style_issues(archive, used_styles, issues):
    """Reject styles that hide or strike text while extraction keeps its words."""
    for name in ("word/styles.xml", "word/stylesWithEffects.xml"):
        if name not in archive.namelist():
            continue
        root = ET.fromstring(archive.read(name))
        styles = {}
        defaults = []
        for style in root.findall(W + "style"):
            ident = style.get(W + "styleId")
            if not ident:
                continue
            inherited = style.find(W + "basedOn")
            hidden = any(node.get(W + "val", "1").lower() not in {"0", "false", "off"}
                         for node in style.iter() if _tag(node) in {"vanish", "webHidden", "specVanish", "strike", "dstrike"})
            styles[ident] = (inherited.get(W + "val") if inherited is not None else None, hidden)
            if style.get(W + "default") == "1":
                defaults.append(ident)

        def hidden_chain(ident):
            seen = set()
            while ident and ident not in seen:
                seen.add(ident)
                parent, hidden = styles.get(ident, (None, False))
                if hidden:
                    return True
                ident = parent
            return False

        affected = sorted(ident for ident in used_styles | set(defaults) if hidden_chain(ident))
        if affected:
            issues.append("Hidden or struck text style requires manual review in " + name + ": " + ", ".join(affected))


def extract(data: bytes, filename: str) -> dict:
    detected = source_format(data)
    suffix = Path(filename).suffix.lower()
    if detected == "pdf":
        if suffix != ".pdf":
            result = _extract_pdf(data, filename)
            result["coverage"]["status"] = "blocked"
            result["coverage"]["issues"].append("File contents are PDF but the filename extension is not .pdf")
            return result
        if len(data) > MAX_SOURCE_BYTES:
            return {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(), "units": [], "coverage": {"status": "blocked", "issues": ["File exceeds the 2 MB local demonstration limit"], "parts": [], "reason": "too_large"}, "size": len(data), "format": "pdf"}
        return _extract_pdf(data, filename)
    if suffix == ".pdf":
        detected_format = detected or "unknown"
        return {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(), "units": [], "coverage": {"status": "blocked", "issues": ["Filename says PDF but the bytes are not a valid PDF"], "parts": [], "reason": "format_mismatch"}, "size": len(data), "format": detected_format}
    result = {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(), "units": [], "coverage": {"status": "complete", "issues": [], "parts": []}, "size": len(data), "format": "docx"}
    issues = result["coverage"]["issues"]
    if len(data) > 2_000_000:
        issues.append("File exceeds the 2 MB local demonstration limit")
        result["coverage"]["status"] = "blocked"
        return result
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            used_styles = set()
            if len(names) != len(set(names)):
                issues.append("Duplicate DOCX part names make source content ambiguous")
            if REQUIRED_PART not in names or any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise ValueError("Invalid DOCX package structure")
            if sum(info.file_size for info in archive.infolist()) > 10_000_000:
                raise ValueError("Expanded DOCX exceeds safety limit")
            for name in names:
                if name.startswith(UNSUPPORTED_PARTS):
                    issues.append("Unsupported content part: " + name)
                elif name.startswith("word/") and name.endswith(".xml") and name not in METADATA_PARTS and name != REQUIRED_PART and not re.fullmatch(r"word/(?:header|footer)\d+\.xml", name) and not name.startswith("word/theme/"):
                    issues.append("Unaccounted Word part: " + name)
                elif name.startswith("customXml/") and name.endswith(".xml") and not "itemProps" in name:
                    custom = ET.fromstring(archive.read(name))
                    if any((element.text or "").strip() for element in custom.iter()):
                        issues.append("Custom XML contains text requiring manual review: " + name)
            parts = [REQUIRED_PART] + sorted(name for name in names if re.fullmatch(r"word/(?:header|footer)\d+\.xml", name))
            for part in parts:
                result["coverage"]["parts"].append(part)
                root = ET.fromstring(archive.read(part))
                used_styles.update(node.get(W + "val") for node in root.iter() if _tag(node) in {"pStyle", "rStyle"} and node.get(W + "val"))
                container = root.find(W + "body") if part == REQUIRED_PART else root
                if container is None:
                    issues.append("Missing document body")
                    continue
                _walk(container, part, result["units"], issues)
            _nonliteral_style_issues(archive, used_styles, issues)
    except (zipfile.BadZipFile, ET.ParseError, KeyError, ValueError, OSError) as exc:
        issues.append("Unreadable DOCX: " + str(exc))
    if issues or not result["units"]:
        result["coverage"]["status"] = "blocked"
        if not result["units"] and not issues:
            issues.append("No extractable text")
    return result


def _walk(container, part, units, issues):
    paragraph_index = 0
    table_index = 0
    for child in container:
        kind = _tag(child)
        if kind == "p":
            paragraph_index += 1
            _paragraph(child, f"{part}:p{paragraph_index}", part, units, issues)
        elif kind == "tbl":
            table_index += 1
            for element in child:
                if _tag(element) not in ("tblPr", "tblGrid", "tr"):
                    issues.append("Unsupported table element " + _tag(element) + " in " + part)
            for row_index, row in enumerate(child.findall(W + "tr"), 1):
                for element in row:
                    if _tag(element) not in ("trPr", "tc"):
                        issues.append("Unsupported table-row element " + _tag(element) + " in " + part)
                for cell_index, cell in enumerate(row.findall(W + "tc"), 1):
                    cell_p_index = 0
                    for element in cell:
                        cell_kind = _tag(element)
                        if cell_kind == "p":
                            cell_p_index += 1
                            _paragraph(element, f"{part}:t{table_index}:r{row_index}:c{cell_index}:p{cell_p_index}", part, units, issues)
                        elif cell_kind == "tbl":
                            issues.append("Nested table requires manual review at " + part)
                        elif cell_kind != "tcPr":
                            issues.append("Unsupported table-cell element " + cell_kind + " in " + part)
        elif kind not in ("sectPr",):
            issues.append("Unsupported document element " + kind + " in " + part)


def _paragraph(paragraph, anchor, part, units, issues):
    for node in paragraph.iter():
        kind = _tag(node)
        if kind in UNSUPPORTED:
            if kind in {"vanish", "webHidden", "specVanish", "strike", "dstrike"} and node.get(W + "val", "1").lower() in {"0", "false", "off"}:
                continue
            issues.append("Unsupported " + kind + " at " + anchor)
    value = _text(paragraph)
    if value:
        units.append({"anchor": anchor, "part": part, "kind": "paragraph" if ":t" not in anchor else "table", "text": value})


def extract_file(path: Path) -> dict:
    return extract(path.read_bytes(), path.name)
