# Local intake and human review walkthrough

For the verified five-case setup, start with [the owner review guide](OWNER_REVIEW.md). It uses the local Python service, fictional DOCX files and isolated state. It does not change the public demonstration.

## Try a fresh upload

1. In **References**, choose **Add fictional Legal reference DOCX**, choose a supported fictional standard, then **Register standard**. This registers one Active library reference. The five-case starter already does this once for its two standards.
2. In **Review queue**, choose **Upload DOCX contracts**. Upload one incoming fictional DOCX or a batch of up to 20.
3. Chug searches Active, integrity-verified references using the incoming family's applicability context. It selects a clear compatible reference and compares automatically for supported NDAs and orders. You do not need to choose a reference for each contract.
4. Open the new queue item. Inspect the selected reference, comparison state, source wording and originals. The comparison is provisional; it does not approve the contract.
5. Where available, **Confirm reference applicability** records a separate human confirmation of the baseline. It is not a prerequisite for the already-completed automatic comparison and does not decide the contract.
6. Assess findings with **Not relevant**, **Acceptable**, **Problem**, **Needs further review** or **Deal breaker**. Then make the separate contract-level choice **Accept contract** or **Flag for further review**. Other outcomes are available in the secondary disclosure. Inspect saved events in **Review history**.

## Honest unresolved case

A file without a suitable Active standard, with conflicting context, missing required facts or incomplete extraction stays in the queue with an explanation and **Comparison not run**. This is not an exact-match result. Inspect the original and resolve the missing context; do not treat it as cleared. Existing reviews retain their original binding; adding a new reference does not silently reanalyse them.

## Current limits

- DOCX only; PDF work in #14/PR #27 remains separate.
- Order comparison reports textual and structural differences, not a legal interpretation of quantities or fees.
- Reviewer labels are self-attested in this local synthetic prototype. Public hosting remains read-only.
- AI is optional and off by default; this intake path does not need a provider key or model call.
- Owner creative acceptance remains pending until the owner records feedback in the guide.

Technical evidence and known matching limits: [INTEGRATED_REVIEW_ACCEPTANCE.md](INTEGRATED_REVIEW_ACCEPTANCE.md). Product flow: [EXPLICIT_REFERENCE_UPLOAD.md](EXPLICIT_REFERENCE_UPLOAD.md).
