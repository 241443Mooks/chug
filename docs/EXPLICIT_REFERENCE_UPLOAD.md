# Automatic reference selection and comparison

The local app searches its active, source-verified reference library when a DOCX arrives. It checks family and applicability facts, excludes incompatible standards, and selects a reference only when a candidate stands ahead.

For supported NDAs and customer orders, comparison runs within the upload request. The selected reference ID/hash and results persist. The match is provisional: a reviewer must check applicability and decide the contract separately.

A tie, conflicting facts, insufficient context, blocked extraction or no eligible standard leaves the original available for review. The result states why comparison did not run. No differences and no comparison are different outcomes.

## Library setup

Register suitable fictional standards once through **References**. Uploaded local standards become active; this is not verified organisational authorisation. The research catalogue remains marked `research_candidate` and is not automatically eligible for incoming reviews.

For two standards and five example intakes:

```sh
python3 scripts/seed_synthetic_starter.py --state-dir ./chug-starter
python3 -m chug.server --port 8771 --state-dir ./chug-starter
```

See the [walkthrough](../START_HERE.md#run-locally).

## Batches and directory intake

The private browser and `POST /api/intakes/batch` accept up to 20 files. Each gets its own compared, awaiting-reference, blocked, duplicate or failed result. Re-delivery retains source hashes and queue identities. Split larger sets into batches.

For a local drop directory:

```sh
python3 scripts/ingest_directory.py --state-dir ./chug-starter --incoming-dir /path/to/private/drop
```

Each invocation scans once and processes DOCX files in groups of 20. The host must supply any schedule. This is not a connected feed or deployed scheduler; private hosting, source connections, concurrency controls and monitoring still need work.

The public static demo cannot accept uploads. Use fictional files only. See the [integration record](INTEGRATED_REVIEW_ACCEPTANCE.md) for tested cases, missed matches and remaining gaps.
