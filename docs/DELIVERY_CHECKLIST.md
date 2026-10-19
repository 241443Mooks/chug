# Submission and handover checklist

PortSwigger's application task requests **a single zipped file** showing how AI could help a small legal team with routine contracts, recurring redlines and month-end/quarter-end review peaks. This is an application exercise, not a request for production legal automation.

**Current status:** the working prototype can be reviewed locally. Human creative acceptance and final clean-package QA remain pending. Possible later product investments in `PRODUCT_DIRECTION.md` are not submission requirements. Package the final ZIP after the owner accepts the experience; do not describe an unobserved live AI run as completed.

## Submission sprint gate — 19 October 2026

**Scope freeze:** finish and prove the contract-review experiment, not a production legal platform. Prioritise the single-ZIP submission required by the application. The public read-only website is supporting evidence, not a submission dependency.

### Release sequence (do not silently promote draft work)

1. **Integrate the core:** review [PR #33](https://github.com/241443Mooks/chug/pull/33) for automatic identification of a single eligible Active reference, provisional NDA/customer-order comparison, real queue persistence and honest abstention. Its branch reports 85 Python tests, 29 UI tests, 6/6 baseline routes and 11/11 critical adversarial cases; GitHub Actions validation passed. **Not yet merged or manually browser-verified.**
2. **Add only necessary human review:** reconcile [PR #25](https://github.com/241443Mooks/chug/pull/25) with #33 (both edit `chug/server.py`, `web/app.js`, `web/styles.css` and `tests/test_web_ui.mjs`); retain per-finding review and contract-level Accept/Flag, with the public demo read-only. Repeat integration tests and manual checks after reconciliation.
3. **Defer PDF unless straightforward:** [PR #27](https://github.com/241443Mooks/chug/pull/27) also edits intake and UI files and requires integration, dependency and browser validation. Stable DOCX is enough for the required core demonstration; document PDF as pending if not accepted.
4. **Prove the flow:** repeat the three-file pilot in [#30](https://github.com/241443Mooks/chug/issues/30), then run a small blinded reference-matching check with answer-key hints removed from source files and metadata ([#31](https://github.com/241443Mooks/chug/issues/31)). Keep hashes, chosen-reference evidence, findings, no-match reasons, restart and duplicate results.
5. **Browser and package:** finish the relevant local/private and public read-only checks from [#9](https://github.com/241443Mooks/chug/issues/9); check the ZIP from a fresh extract; conduct human creative review; give final explicit go/no-go.

### Minimum acceptance scenarios

- [ ] Exact NDA automatically selects the appropriate Active NDA reference; comparison reports no differences; human action stays pending.
- [ ] Changed NDA automatically selects the appropriate NDA reference; altered wording is evidenced and available for human review.
- [ ] Exact customer order automatically selects the appropriate Active order reference; comparison reports no differences; human action stays pending.
- [ ] Changed customer order automatically selects the appropriate order reference; altered commercial terms are evidenced and available for human review.
- [ ] Ambiguous, unsupported or inapplicable document abstains with a helpful reason; comparison is `not_run`, not falsely complete.
- [ ] Repeat and restart preserve immutable originals, hashes, reference bindings and review states; critical T03/T04/T05 safeguards continue to pass.
- [ ] Small *blinded* NDA/order matching sample records correct proposals, correct abstentions, wrong proposals and unnecessary abstentions against a withheld answer key.
- [ ] Local/private reviewer actions persist correctly; the publicly accessible demo cannot save decisions or accept uploads.
- [ ] A fresh-extracted submission ZIP runs as documented and contains no secrets, credentials or private records; its SHA-256 is recorded.
- [ ] Genuine AI use, live verification status, privacy implications and non-AI baseline are represented accurately without inventing legal validation or time savings.

### Deliberately out of scope for this submission

- Full 200–300 document corpus ([#34](https://github.com/241443Mooks/chug/issues/34)).
- External feed connectivity, scheduler and operational monitoring ([#35](https://github.com/241443Mooks/chug/issues/35)).
- Enterprise load tests, production legal workflows, additional document families and new AI features.
- Full 20-file import ([#16](https://github.com/241443Mooks/chug/issues/16)) unless the small pilot and core browser checks pass and it adds useful evidence.

**Stop rule:** five honest demonstrations, preserved evidence and human oversight, passing critical safety checks, truthful limitations, a usable local walkthrough and a verified ZIP. Do not extend the implementation solely to eliminate every future-product issue. A reported limitation is preferable to a misleading claim of completion.

**Status language as at 19 October 2026:** draft PRs #25, #27 and #33 have individually passed GitHub Actions validation. Their combined behaviour, rendered browser acceptance, blinded matching and ZIP packaging are **not verified**. No deployment or merge is implied by this document.

## Reviewer experience
- [ ] Start with a short `START_HERE.md` explaining the problem, approach, why conventional engineering handles much of it, and where the genuine AI contribution earns its place.
- [ ] Provide a five-to-ten-minute guided walkthrough: routine NDA, context-limited precedent, hidden critical amendment, queue prioritisation, human decision.
- [ ] State what is deterministic, what uses a real model, the baseline and business justification for that choice, and what always requires a person.
- [ ] Include clear instructions for running locally with and without optional configured AI access; offline mode must not impersonate AI.
- [ ] Show how the design could reduce repetitive review and handle peaks; do not invent measured time savings.
- [ ] Explain limits, privacy and why this is not legal advice.

## Technical deliverable
- [ ] One ZIP with runnable source, required dependency manifests, synthetic documents, review register, evaluation instructions and reviewer walkthrough.
- [ ] Clean checkout/install/start succeeds with documented commands.
- [ ] Tests execute and report meaningful results; safety cases T03/T04/T05 pass or failure is prominently disclosed.
- [ ] Actual model integration available with explicit opt-in and provider setup; report if live test unverified.
- [ ] Full originals available, evidence navigation working, review queue usable, decisions auditable.
- [ ] No keys, tokens, local `.env`, private records, sensitive logs, caches, virtual environments, build clutter or unnecessary generated artifacts.
- [ ] Include exact commands, supported Python version, known limitations and dependency constraints.

## Git workflow
- [ ] Work on a feature branch; keep commits coherent and reviewable.
- [ ] Draft PR includes milestone evidence and outstanding issues.
- [ ] Do not merge automatically.
- [ ] Record ZIP creation command and checksum.
- [ ] Confirm the ZIP can be opened and contents inspected independently.
- [ ] Do not submit or upload to the employer automatically.

## Creative QA
- [ ] Reviewer sees what changed, why it matters, relevant history and next action without a wall of text.
- [ ] Full evidence is one interaction away; no shortcut hides missing coverage or failed checks.
- [ ] Human creative review is completed or clearly marked pending; document insights in `docs/DESIGN_JOURNAL.md`.
- [ ] The result feels simple on the surface and robust underneath, not like a generic AI dashboard.

## Final QA
An independent reviewer should be able to answer within ten minutes: What problem does this solve? Where is real AI used? What safeguards exist? Can I run it? What evidence shows it works? What are its limitations?
