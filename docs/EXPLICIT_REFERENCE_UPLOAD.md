# Automatic reference selection and comparison on upload

The local/private synthetic workspace searches its **Active, integrity-verified reference library** when a user uploads an incoming DOCX. No per-contract reference selection is needed. Chug extracts the document family and applicability facts, excludes incompatible references, and uses source-supported scope ranking when more than one candidate remains. It selects a reference only when one candidate stands ahead. A tie, conflicting source facts, missing required context, blocked extraction, or no eligible reference leaves the incoming original in the queue with `comparison: not_run` and a reason.

The same pipeline accepts up to 20 files in one private browser batch (`POST /api/intakes/batch`). Each file gets its own result: compared, awaiting reference, blocked extraction, duplicate or failed. An invalid file does not hide the results of the others. Repeating a batch uses the same source hashes and queue IDs. Larger sets can be sent in batches of 20.

For a directory feed, run `python3 scripts/ingest_directory.py --state-dir /tmp/chug-starter --incoming-dir /path/to/private/drop` on a schedule supplied by the private host. Each invocation scans the drop directory once, processes DOCX files in groups of 20 through the same intake method, and reports per-file states as JSON. Repeated delivery is idempotent. This is a local adapter, not a connected email/feed service or a deployed scheduler; those will need a private host, source connection, concurrency controls and operational monitoring.

For a supported NDA or customer order with a suitable Active reference, the server compares the two original documents **within the upload request**. The comparison and selected reference ID/hash survive restart. The queue displays source-linked differences or states that none were reported. This result is **provisional**: Chug has proposed a reference, not verified legal applicability or accepted the contract. A reviewer may confirm reference applicability separately and must independently decide the contract. Zero differences do not automatically approve it.

The fictional research catalogue remains marked `research_candidate`. Registering a chosen specimen as an Active fictional standard is a one-time controlled library setup; it does not elevate the research record or require a user to classify each subsequent incoming contract. The public static site remains read-only and cannot accept uploads. No private hosting or bulk import is included here.

For a repeatable local starter workspace, run `python3 scripts/seed_synthetic_starter.py --state-dir /tmp/chug-starter` from the repository root, then start the local server against that state directory. The script registers two fictional standards and creates five real queue intakes (an exact copy and a changed example for each family, plus an ambiguous purchase that should abstain with comparison not run). It passes no reference ID to intake, so it exercises automatic selection. Re-running it keeps the same source-bound queue records.

## Demonstrated paths

- Registered Product Evaluation NDA → incoming evaluation NDA with longer retention: automatic NDA match and source-linked comparison findings.
- Registered Reseller Desktop customer-order standard → incoming desktop reseller seat increase: automatic customer-order match and two observations.
- Exact copies of either standard: zero reported differences, with human review pending.
- Ambiguous reseller cloud purchase: no suitable matching standard, no comparison and no automatic approval.

These are fictional synthetic examples. The next corpus step is one or two independently checked exact-match incoming examples for each of the eight research reference variants, followed by changed-term and difficult cases. Keep the withheld answer key outside runtime inputs, complete the blinded matching check, and then grow toward 200–300 fictional contracts in measured batches.
