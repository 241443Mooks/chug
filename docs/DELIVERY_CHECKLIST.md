# Submission checklist

The application task asks for one ZIP showing how AI could help a small legal team review routine contracts. The website is supporting material. The submission is a prototype, not a production service.

## Position on 19 October 2026

PR #37 merged automatic comparison and human review into main. The [integration record](INTEGRATED_REVIEW_ACCEPTANCE.md) contains the three-file pilot, blinded matching results and local browser checks. It records three missed matches as well as the successful cases. PDF support, broader matching, owner acceptance and final ZIP verification remain separate work.

## Before packaging

- [ ] Owner reviews the [five local examples](../START_HERE.md#run-locally) and records feedback using the [review checklist](CREATIVE_REVIEW.md).
- [ ] Verify the exact submitted revision: Python tests, UI tests, baseline routes and critical adversarial cases. Record failures and limits.
- [ ] Confirm originals, reference bindings, findings, human actions, restart and duplicate handling still work. Public examples must remain read-only.
- [ ] Describe the optional real-provider adapter, non-AI baseline and data transmission accurately. Mocked tests do not establish a live result or useful legal explanation.
- [ ] Keep setup instructions and capability claims consistent with the submitted code. Do not claim measured savings, legal validation or production security.

## ZIP checks

- [ ] Include runnable source, required dependencies, fictional examples, test instructions, licence and walkthrough.
- [ ] Exclude keys, tokens, local state, private records, logs, caches, environments and build clutter.
- [ ] Extract into a fresh directory and run the documented setup and checks.
- [ ] Record the source revision, packaging command and ZIP SHA-256.
- [ ] Check that another person can open the ZIP and follow the walkthrough.

The larger corpus, connected feeds, scheduler, production hosting and extra contract families are outside this submission. PDF support is optional; stable DOCX is sufficient for the core demonstration.

Prepare changes on a branch with a reviewable PR. Do not merge, deploy or submit to the employer automatically. Final acceptance and submission remain with the owner.
