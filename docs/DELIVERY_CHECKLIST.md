# Submission and handover checklist

PortSwigger's application task requests **a single zipped file** showing how AI could help a small legal team with routine contracts, recurring redlines and month-end/quarter-end review peaks. This is an application exercise, not a request for production legal automation.

**Current status (19 October 2026):** integration PR #37 is merged into main at `477737d`, with passing main validation. The working prototype is ready for local owner review. Human creative acceptance and final clean-package QA remain pending. Today's bounded work is tracked in [the day plan](DAY_PLAN_2026-10-19.md); use [the five-case owner guide](OWNER_REVIEW.md) for the next review session. Possible later product investments in `PRODUCT_DIRECTION.md` are not submission requirements. Package the final ZIP after the owner accepts the experience; do not describe an unobserved live AI run as completed.

## Submission sprint gate — 19 October 2026

**Scope freeze:** finish and prove the contract-review experiment, not a production legal platform. Prioritise the single-ZIP submission required by the application. The public read-only website is supporting evidence, not a submission dependency.

### Release sequence

1. **Core integrated:** #33 and #25 were combined and merged through [PR #37](https://github.com/241443Mooks/chug/pull/37). Automatic reference selection, provisional NDA/order comparison, persisted intake queue and per-finding/contract review work together. Main validation passed.
2. **Local technical checks complete:** 97 Python and 34 UI tests passed in the integration run; baseline routes 6/6, critical adversarial cases surfaced 11/11, overall adversarial route agreement 14/16. Desktop/mobile private and local public-static browser checks passed. This is not owner acceptance or deployed-site verification.
3. **Small matching exercise recorded:** the three-document HTTP pilot passed; ten blinded fixtures produced 5 correct matches, 2 correct abstentions, no wrong matches and 3 unnecessary abstentions. The key was agent-authored. Broader order matching and independent human annotation remain open, with limits recorded rather than hidden.
4. **Owner review next:** follow [OWNER_REVIEW.md](OWNER_REVIEW.md), record actual feedback and fix submission blockers. Finish the explanation of deterministic functionality, optional AI and live-verification status.
5. **Package after acceptance:** reconcile packaging PR #36 with the final candidate, inspect archive contents, fresh-extract and run the documented journey, record its checksum, then seek the owner's final readiness decision. PDF #27 remains deferred.

### Minimum acceptance scenarios

Checked boxes below mean observed technical behaviour in the merged integration, not completed owner review. Owner feedback remains in [the owner guide](OWNER_REVIEW.md).

- [x] Exact NDA automatically selects the appropriate Active NDA reference; comparison reports no differences; human action stays pending.
- [x] Changed NDA automatically selects the appropriate NDA reference; altered wording is evidenced and available for human review.
- [x] Exact customer order automatically selects the appropriate Active order reference; comparison reports no differences; human action stays pending.
- [x] Changed customer order automatically selects the appropriate order reference; altered commercial terms are evidenced and available for human review.
- [x] Ambiguous, unsupported or inapplicable document abstains with a helpful reason; comparison is `not_run`, not falsely complete.
- [x] Repeat and restart preserve immutable originals, hashes, reference bindings and review states; critical T03/T04/T05 safeguards continue to pass.
- [x] Small *blinded* NDA/order matching sample records correct proposals, correct abstentions, wrong proposals and unnecessary abstentions against a withheld answer key.
- [x] Local/private reviewer actions persist correctly; the local public-static export exposes no save forms or upload controls and made zero POST requests during the rendered check. The deployed website was not verified in that run.
- [ ] A fresh-extracted submission ZIP runs as documented and contains no secrets, credentials or private records; its SHA-256 is recorded.
- [ ] Genuine AI use, live verification status, privacy implications and non-AI baseline are represented accurately without inventing legal validation or time savings.

### Deliberately out of scope for this submission

- Full 200–300 document corpus ([#34](https://github.com/241443Mooks/chug/issues/34)).
- External feed connectivity, scheduler and operational monitoring ([#35](https://github.com/241443Mooks/chug/issues/35)).
- Enterprise load tests, production legal workflows, additional document families and new AI features.
- Full 20-file import ([#16](https://github.com/241443Mooks/chug/issues/16)) unless the small pilot and core browser checks pass and it adds useful evidence.

**Stop rule:** five honest demonstrations, preserved evidence and human oversight, passing critical safety checks, truthful limitations, a usable local walkthrough and a verified ZIP. Do not extend the implementation solely to eliminate every future-product issue. A reported limitation is preferable to a misleading claim of completion.

**Integration checkpoint, 19 October 2026:** #37 is merged at `477737d`; [the integration report](INTEGRATED_REVIEW_ACCEPTANCE.md) preserves the dated pre-merge results. PDF #27, broader matching, owner creative acceptance, final AI explanation and ZIP packaging remain pending. A merge does not verify a Cloudflare deployment.

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
