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
    result = {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(), "units": [], "coverage": {"status": "complete", "issues": [], "parts": []}, "size": len(data)}
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
