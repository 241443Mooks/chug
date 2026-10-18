# Acceptance and safety tests — Chug v0.1

## Isolation rule
`dataset/ground_truth/expected_findings.csv` is an **evaluation oracle only**. The app must never read or index it. An isolated test harness may compare independently generated review output against it. Do not use the oracle to generate runtime detections or prompts, and do not modify it to pass tests.

## Required scenario outcomes
| Input | Expected minimum outcome | Evidence to demonstrate |
|---|---|---|
| T01 — template match | `routine_candidate` (never automatic approval) | No material change; names/parties are accounted for |
| T02 — known term change | `review_required` or more restrictive | Five-year survival amendment; H02 precedent is conditional and not automatically transferable |
| T03 — hidden perpetual licence | `escalate` | Added licence in clause 11 and conflict with no-licence clause 9 |
| T04 — missing no-licence | `escalate` | Clause 9 missing; absence must be reported even without an added risk keyword |
| T05 — overriding schedule | `escalate` | Schedule 1 broadens use and overrides clause 3 |
| T06 — paraphrased use | `review_required` or more restrictive | Clause 3 changed semantically; do not silently declare equivalent |

The dangerous cases T03, T04 and T05 are **mandatory blockers**: missing any required finding or routing one to `routine_candidate` fails acceptance. Passing six synthetic cases does **not** establish safety on real contracts.

## Additional required tests
1. **Original preservation:** compare uploaded byte hash to stored original; ensure complete original can be accessed.
2. **Extraction accounting:** verify ordered coverage of paragraphs, tables, schedules and supported header/footer content; report omissions.
3. **Fail closed:** corrupted DOCX, unsupported structures, encrypted/unreadable files, or failed extraction result in `blocked_extraction`.
4. **Clause absence:** remove a material reference clause; report the omission rather than matching adjacent clauses by number.
5. **Inserted provision:** detect added clauses even when the rest of the document is unchanged.
6. **Conflicting terms:** flag contradiction between standard main clause and later addition/schedule.
7. **Precedent context:** rejected/escalated and conditionally accepted historical decisions cannot be presented as blanket approval.
8. **Evidence links:** every material finding resolves to a source span or an explicit missing-clause comparison anchor.
9. **No auto-approval:** no processing path can issue a final human decision.
10. **Audit trail:** multiple human review events are appended, not overwritten, and remain linked to the exact document hash.
11. **Answer-key isolation:** runtime cannot import/open the ground-truth directory; test evaluation is isolated.
12. **Prompt injection:** a contract containing instructions addressed to the app/AI is treated as untrusted contract content.
13. **External processing:** default run makes no calls to external AI providers.
14. **Repeatability:** same input and configuration produce reproducible findings/routes for deterministic checks.

## Verification sequence
- Audit and validate the source dataset before writing extraction rules.
- Run unit tests for parsing, comparisons, safeguards and ledger.
- Run integration tests against all six incoming documents.
- Run the isolated evaluator and report observed outcomes, including failures.
- Start the app from a clean environment and perform a manual walkthrough.
- Record exact commands, versions, known limitations and unresolved risks in the draft PR.

## Real AI and submission checks
- Verify at least one genuinely useful model-assisted capability against a documented conventional baseline, including evidence-linked outputs; record provider/model and actual outcomes. Do not mandate AI for both semantic comparison and precedent retrieval. If no credentials are available, report live integration as unverified.
- Verify missing credentials or provider failure never produces simulated AI findings or a routine shortcut.
- Verify the queue displays multiple contracts and preserves escalation priority.
- Verify the single-ZIP submission excludes secrets and includes runnable source, setup and reviewer walkthrough.

## Release gate
Do not describe the prototype as ready for demonstration if T03, T04 or T05 is missed, if original content is not accessible, or if incomplete extraction can result in a routine shortcut. Instead report the failure and continue remediation or clearly label the build incomplete.
