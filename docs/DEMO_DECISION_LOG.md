# Fictional historical decision log — demonstration only

A separate browseable set of **300 entirely invented** past decision scenarios illustrates how recurring review questions, red flags, resolved exceptions, and conditional choices could support later human judgement. It is **not** a record of actual legal review work.

## Open it
- Static demo: `/decision-log.html`; navigate from the Decision log link in the header. Filter by six incoming cases, prior outcome, or a search term.
- Local Python demo: the same `/decision-log.html` path is read-only, served from an explicit allowlist.
- To rebuild the static snapshot: `python3 scripts/export_public_demo.py`. This copies only the reviewed fictional source fixture, never `.chug-data/decisions.jsonl` or actual local decisions.

## What the data is
- `dataset/review_records/demo_decision_log.json` is the canonical fictional fixture. `web/demo-data/decision-log.json` is the static copy.
- 45 examples connected to T01, 50 to T02, 65 to T03, 45 to T04, 45 to T05, and 50 to T06.
- Every entry identifies a fictional reviewer/counterparty/date, previous human action, rationale, conditions, relation to an existing incoming scenario, and when appropriate one of the five existing fixed historical examples (H01–H05).
- A **related current review** link opens the live synthetic review. A **related fixed example** link opens an existing source DOCX when present. That DOCX is **not evidence** that the separate invented decision took place.
- Prior `green` describes a fictional acceptable or *amended* version; it is never authority to accept today's differing text. `red` describes an earlier problematic pattern. `amber` describes cases requiring context.
- The local `Ledger`, `KnowledgeLedger`, decisions and review routes are deliberately unchanged. These unverified scenarios are not fed into the precedent ranker and cannot influence routing or auto-approve anything.

## How this differs from real organisational learning
This is a visual volume-and-pattern prototype. Genuine precedents would require unique original evidence, reviewer identity, complete decision history, context, authority, version status and explicit publication before entering retrieval. A human legal team would need to approve taxonomy and policy. The current synthetic 300-entry log is **not** source-backed legal experience and should never be advertised as validated learning or measured review effectiveness.

## Verification
Run `python3 -m unittest tests.test_demo_decision_log -v`, then the repository regression tests. The static export validates record count, IDs, provenance markers, and links. Browser rendering and mobile usability still require human inspection before accepting the creative outcome.
