# Automatic comparison and human review — integration acceptance

19 October 2026. Draft integration of PR #33 (`1879bcd`) and PR #25 (`e0e8839`), including current main's submission scope freeze. Local synthetic DOCX only. PDF PR #27 is separate.

## Result

Automatic selection/comparison and human finding assessments/contract actions now run in the same version. The three-document pilot and rendered private/public workflows pass locally. The blinded fixture check records **5 correct matches, 2 correct abstentions, 0 wrong matches and 3 unnecessary abstentions**. This is a limited fixture result, not general matching accuracy or legal validation.

This is ready for owner review as a draft integration. It is not a production or final submission acceptance: broader order matching, human creative review and fresh ZIP verification remain outstanding. Nothing was merged into main or deployed by this acceptance run.

## Integration fixes

- Keep #33's automatic, provisional NDA/order comparison and batch results; do not fabricate a human applicability confirmation on upload.
- Keep #25's five finding assessments, separate Accept contract/Flag for further review, original-review acknowledgement and unresolved-finding acceptance checks.
- Fix uploaded-review submit handlers: a document-level listener passed the wrong `currentTarget` to `FormData`, so the browser could not save. Bind each form directly, once. Browser assertions verify exactly one POST per action.
- Keep customer-order reference excerpts in the assessment evidence snapshot; bind the actual reference ID/hash rather than its display label. Missing-section findings can use reference-only evidence without inventing an incoming passage.
- Show saved finding revisions, contract actions and other recorded outcomes in uploaded-review history. Expose full verified reference wording and both exact original downloads.
- Fix the finding route to retain its precise ID. Without this, the new finding page displayed “unavailable” after clicking a summary or following a deep link.
- Fix narrow-screen uploaded-review layout/hash wrapping and the public comparison-count overflow. Keep public navigation usable and mutations unavailable.

## Separate three-document HTTP pilot

[`integrated-three-document-pilot.json`](evidence/integrated-three-document-pilot.json) records full incoming/reference hashes, queue IDs and finding titles.

The acceptance runner starts an actual Python service with fresh persistent state, registers only the two selected fictional standards through HTTP and submits the three original files to the batch endpoint. It does not call the starter seeding helper or a matcher-only shortcut. Its process is separate from the unit tests. The same agent authored and ran this acceptance; no separate human/external review is claimed.

| Incoming original | Automatic result | Differences | Human state before test actions |
| --- | --- | ---: | --- |
| Evaluation NDA with Longer Retention | Correct evaluation NDA reference; comparison analysed | 4 | Pending; no fabricated confirmation |
| Desktop Reseller Seat Increase | Correct reseller desktop reference; comparison complete | 2 | Pending; no fabricated confirmation |
| Ambiguous Reseller Cloud Scan Purchase | No suitable reference; comparison not run | Not assessed | Pending |

All 3 originals and both linked reference downloads matched their SHA-256 values. A cold service restart preserved the full detail records. Re-delivering all 3 produced 3 duplicates, unchanged queue identities and no extra intake entries. No failures or silent drops.

The raw differences include specimen presentation changes: the NDA has three header/record changes plus its substantive archive provision; the order has an introductory-section change plus the 25-to-60-seat change. These counts are not counts of legal risks.

The rendered browser run separately exercises human confirmation of both the NDA and order reference after automatic analysis, preserving the earlier assessment and pending human decision. Confirmation and acceptance are distinct operations.

## Blinded matching check

[`integrated-blinded-matching.json`](evidence/integrated-blinded-matching.json) contains every input hash, expected/selected reference hash, outcome and reason.

1. Declare an expected reference from the substantive source context for one routine example of each of the eight reference variants, plus a reseller-cloud negative and a new context-free negative.
2. Rebuild incoming DOCX files under opaque names. Remove `Proposed reference`, `Standard family`, document IDs, original filenames and all core/custom/header/footer properties by constructing a minimal DOCX with only body content and package relationships. Retain ordinary agreement titles, parties and substantive clauses. Scan every ZIP member for catalogue reference IDs and prohibited hints. ZIP timestamps are fixed for repeatability.
3. Write a separate expected-outcome key before running the matcher. The key is agent-authored, not an independent human annotation. The runtime manifest contains only document and reference paths; neither the server nor the HTTP runner imports the preparation/evaluation scripts or reads the key or `evaluation-only/expected-matches.json`.
4. Register all eight deliberately selected fictional Active standards in fresh state; submit the ten blinded files through the actual HTTP intake path. Freeze results before the separate evaluator reads the key.
5. Restart and redeliver: all 10 originals persist and all 10 repeat deliveries deduplicate.

| Opaque file | Source context | Outcome |
| --- | --- | --- |
| q7 | Mutual evaluation NDA | Correct match |
| m2 | Mutual supplier NDA | Correct match |
| v9 | One-way customer NDA | Correct match |
| h4 | Direct desktop order | Correct match with stated gaps |
| t8 | Managed cloud order | Unnecessary abstention: no suitable match |
| a3 | Self-hosted order | Unnecessary abstention: conflicting context |
| z6 | Combined desktop/cloud order | Unnecessary abstention: no suitable match |
| d1 | Reseller desktop order | Correct match with stated gaps |
| r5 | Unsupported reseller-cloud purchase | Correct abstention |
| x0 | No identifiable contract context | Correct abstention |

**Denominators:** correct matches 5/8 expected-match cases; correct abstentions 2/2 negative cases; wrong matches 0/10; unnecessary abstentions 3/8 expected-match cases. Five documents compared and five stayed awaiting reference. All human decisions remained pending. The three failures remain recorded; the matcher was not tuned against these held-out results. This is answer-key-blinded input testing, not a new external corpus or independent human benchmark. Broader order coverage in #31/#34 remains open. Do not turn this into an unrestricted 20-file rollout claim.

## Rendered browser verification

Private: actual loopback Python backend with fresh state and real browser uploads. Public: freshly exported static files served locally under a simulated public hostname; no Python API available to that public surface. The deployed `chug.smooks.co.uk` was not tested or changed.

The Browser plugin runtime was not exposed; the available cloud browser returned `ERR_CONNECTION_REFUSED` for the local service. Local Playwright used a temporary Chromium binary (153.0.8010.0). No browser dependency was added to the project. Evidence: [`integrated-private-browser.json`](evidence/integrated-private-browser.json), [`integrated-public-browser.json`](evidence/integrated-public-browser.json). Screenshots were captured and inspected during the run; they are not committed assets.

| Check | Private result | Public static result |
| --- | --- | --- |
| Identity, meaningful content, no error overlay | Pass | Pass |
| App console/page errors | None | None |
| Desktop 1440×1000 and mobile 390×844 | Pass; no page overflow | Pass; no page overflow |
| Main interaction | Upload references → batch → comparison → assess → flag → history | T05 direct link → finding 2 → example choices → back → comparison → refresh |
| Exact-match cases | NDA and order auto-compare with zero differences and pending decision | Existing fictional snapshots remain inspectable |
| Human acceptance | Exact NDA requires original-review checkbox; action and history persist | No visible save forms or upload controls; zero POST requests |
| Restart / refresh | Cold process restart preserves assessments, flag and confirmations | Direct link and comparison refresh work |
| Keyboard | Enter activates queue/back controls on mobile | Navigation checked through real controls |
| Original downloads | Incoming/reference hashes verified in browser | Export originals retain fixture provenance |

The private browser run also records a customer-order assessment with both 60-seat incoming and 25-seat reference wording. No assessment itself approves the contract. Human flags remain pending. The fresh public export contains no locally entered review records; all finding-assessment and contract-action arrays are empty. Screen-reader, other browser engines, real phone hardware, private live hosting and owner creative acceptance remain unverified.

## Automated checks

- Python regression suite: **97 passed**.
- Node UI suite: **34 passed**.
- Six baseline routes: **6/6**.
- Critical adversarial cases surfaced: **11/11**; false-routine recommendations on critical cases: **0**; route agreement **14/16**, with two unnecessary escalations. Existing noncritical limitations remain.
- JavaScript syntax and `git diff --check`: passed.

## Reproduce

Run from the repository root. Use new directories for every HTTP acceptance run; the runner refuses an existing workspace. The preparation/evaluation files must never become runtime application inputs.

```bash
python3 scripts/prepare_integrated_acceptance.py --workspace /tmp/chug-check-inputs
python3 scripts/verify_integrated_intake.py /tmp/chug-check-inputs/pilot-manifest.json --workspace /tmp/chug-check-pilot
python3 scripts/verify_integrated_intake.py /tmp/chug-check-inputs/blind-manifest.json --workspace /tmp/chug-check-blind
python3 scripts/evaluate_integrated_matching.py /tmp/chug-check-inputs/withheld-key.json /tmp/chug-check-blind/captured-results.json /tmp/chug-check-evaluation.json
python3 -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/test_web_ui.mjs
python3 -m tests.evaluate
python3 -m tests.adversarial_audit
```

For rendered checks, use an existing Playwright installation and a compatible Chromium executable. The scripts start and stop their own loopback-only service; they do not deploy anything. Evidence directories hold browser output and screenshots outside the repo.

```bash
CHUG_CHROMIUM_EXECUTABLE=/path/to/chromium node scripts/browser_integrated_review.cjs /tmp/chug-private-evidence
python3 scripts/export_public_demo.py
CHUG_CHROMIUM_EXECUTABLE=/path/to/chromium node scripts/browser_public_review.cjs /tmp/chug-public-evidence
```

The refreshed static export is included in this branch. Final merge/deployment, owner review and ZIP acceptance are separate gates.
