# Decision 003 — Conservative text-based PDF ingestion

## Problem

Fictional references and incoming contracts sometimes arrive as PDFs. The
existing family matcher and comparators already operate on ordered source units,
so PDF ingestion should produce that shared contract while preserving the
received bytes and page-level evidence.

## Options and baseline

- Keep DOCX-only: lowest maintenance, but excludes common received source files.
- Convert PDF to DOCX: changes the source container and loses reliable original
  page anchors and signature bytes.
- Use a local PDF parser: preserves source identity and supports text extraction
  without sending contract text elsewhere.

## Selection

Use pypdf 6.21.1 under its BSD 3-Clause license. The parser runs locally and
does not execute PDF actions or resolve external references. It emits ordered
line units with `pdf:p<page>:l<line>` anchors and keeps the existing
`filename/sha256/units/coverage/size` extraction fields. DOCX extraction and its
anchors remain unchanged.

## Safety and limits

The local limit is 2 MB and 100 pages, with a 1,000,000-character extraction
cap plus parser-level stream, decompression, object-count and work limits.
Encrypted, malformed, image-only, image-bearing, annotation-bearing,
active-content, optional-layer, form-field, table-like or column-ambiguous PDFs
are retained on intake where possible but marked blocked, excluded from
matching and comparison, and cannot become Active references. A signature-only
field is disclosed; cryptographic validity and signatory identity are never
asserted. Original bytes are stored by SHA-256 with the original extension and
served with PDF media type after a fresh hash check.

Clean text extraction does not visually verify vector marks or page rendering.
Reviewers can inspect the exact original. OCR and signature verification are
out of scope. The public static demo remains read-only.

## Verification

Synthetic tests cover cross-format family/context matching, page anchors,
provision changes, original hash and download, persistence, malformed and
image-only PDFs, and format mismatch. These tests do not prove extraction on
real client documents or legal accuracy.
