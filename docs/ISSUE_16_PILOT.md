# Issue #16 — Controlled three-document intake pilot

**Run:** 18 October 2026  
**Source:** clean clone of `origin/main` at `541925117e01bbc3404bb80f3d265a6818260d0e` (PR #22)  
**Runtime:** local Python app on `127.0.0.1:8771`  
**State:** isolated at `/private/tmp/chug-issue16-current-state`; synthetic documents only

## Scope and setup

This was the requested 3-file pilot only. No routine-client bulk batch, 4-file challenge batch, adversarial intake batch, deployment, or Cloudflare change was performed. The files were posted one at a time to the same `POST /api/intakes` route used by the local UI, then opened in the local browser queue. Three existing baseline NDA records remained in the same queue alongside the pilot entries; the queue showed 9 items total.

The research catalogue was not promoted wholesale. A controlled attempt to register only the matching Product Evaluation NDA by the local reference upload route was rejected because its headings do not match the legacy NDA clause family. Re-uploading the selected Reseller Desktop reference returned the existing `research_candidate` record (`ORDER-RESELLER`, SHA-256 `25faa37169e381da193d6e353b77c84aec9ca091e86c4a167d18e998cdd03fa1`); it remained unapproved and ineligible. No source document or reference metadata was changed.

## Per-document results

| Incoming file | Extracted family / match result | Queue status and comparison | Identity and human state |
|---|---|---|---|
| `Incoming - Evaluation NDA with Longer Retention.docx` | NDA; context extracted as mutual, product evaluation, England and Wales. No Active eligible match; Product Evaluation NDA remained a research candidate. | `review_required`, `awaiting_reference`; comparison `not_run`; reason: no reference matches extracted family and applicability context. | Queue ID `I-9f1be3a46a`; SHA-256 `9f1be3a46af4074d4e986ae200f3c49a22b70aca7c0d2e1e604e8737bfcbb81a`; human decision pending. |
| `Incoming - Desktop Reseller Seat Increase.docx` | Family unresolved despite the reseller/desktop order content; no reference proposal. | `review_required`, `awaiting_reference`; comparison `not_run`; reason: agreement family is not explicit in extracted source. | Queue ID `I-382fa40007`; SHA-256 `382fa40007ca24b7894b155874a504d41940ee775b757f6ae7040b8cc6eb393f`; human decision pending. |
| `Incoming - Ambiguous Reseller Cloud Scan Purchase.docx` | Family unresolved; matcher asks whether this is an NDA or customer order. No reference proposal. | `review_required`, `awaiting_reference`; comparison `not_run`; reason: agreement family is not explicit in extracted source. | Queue ID `I-360def80fc`; SHA-256 `360def80fc88cef8212e2bfb83e9985acf42e1d07cd74d9db241733a6e4ead90`; human decision pending. |

All three extractions reported complete body coverage. The detail screens showed the source hash, pending human decision controls, and an exact-original download. No green/routine result or automated decision was produced. Because no Active proposal was available, the customer-order confirmation safeguard could not be exercised through its positive path; no confirmation was fabricated.

## Duplicate and restart checks

- Reposting the exact NDA bytes after the service restart returned the original ID `I-9f1be3a46a`; the intake count remained 3 and the queue remained 9 total. No prior item or review state was overwritten.
- Restarted the local app against the same isolated state directory. All 3 intake entries reloaded with their original IDs, routes, `awaiting_reference` status, pending decisions, and hashes.
- Compared each stored `.docx` byte hash with its source file: all 3 matched.
- No review decisions were recorded during the pilot.

## UI walkthrough and friction

Opened the mixed queue and all three intake detail screens in the local browser. The detail view made `Comparison not run`, the reason, the hash, the next human step, the decision form, and original download visible. Screenshots of the restored queue and the NDA detail were captured in the pilot conversation; no screenshot binary was added to the repository.

Observed friction: at `#queue`, the workspace copy says “This public demo cannot save decisions” even on the local app, while the local queue and detail screens do support saved decisions. The queue list was available in the accessibility tree and its entries opened, but the queue screenshot showed an empty workspace area beside the list. A reviewer may interpret the stale public-demo wording as a local restriction. This should be checked during owner walkthrough before changing the UI.

## Verification

- `python3 -m unittest tests.test_intakes -v` — 9 passed.
- `python3 -m tests.evaluate` — T01–T06 route agreement 6/6.
- `python3 -m tests.adversarial_audit` — critical exception recall 11/11; false routine recommendations 0; expected route matches 14/16; 2 unnecessary escalations among 9 review/routine targets.
- Live model calls: none.
- Blinded matching subset: not run. No Active family references were available, so this pilot cannot establish matching accuracy.

## Outcome and next step

The intake path durably queues the three documents, preserves their bytes, deduplicates the repeated NDA, and fails closed with pending human action. However, the NDA reference could not be registered through the present local path, and both order examples were classified as family-unknown. The pilot therefore did not reach confirmed order comparison or analysed NDA comparison. Do not start the 20-file batch yet. First resolve reference registration for selected research specimens and establish why explicit order content is not producing a family, then repeat this small pilot and test the positive customer-order confirmation path.

No legal conclusion, matching accuracy claim, or owner creative acceptance is implied by this technical exercise.
