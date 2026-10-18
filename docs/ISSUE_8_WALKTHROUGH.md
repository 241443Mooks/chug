# Issue #8 — Local intake and review walkthrough

This walkthrough uses synthetic DOCX files with the local Python service. It does not change the static public demonstration.

## Start

From the repository root:

```sh
python3 -m chug.server --port 8771
```

Open `http://127.0.0.1:8771`. Use fictional documents only.

## Completed provisional NDA comparison

1. In **Reference**, upload a fictional NDA standard whose family and purpose match the incoming NDA. Local uploads are marked Active in this prototype; applicability still needs a reviewer.
2. Return to the queue and choose **Add DOCX**. Upload a new fictional NDA using that same scope.
3. Open the new queue item. Check the proposed reference ID, version, SHA-256 and source-linked applicability evidence.
4. Review the deterministic comparison. Confirm the changed incoming and reference excerpts and their anchors. The comparison is provisional until a reviewer confirms the proposed baseline; it never approves the contract.
5. Record a human decision with a reviewer name and rationale. The append-only event is linked to the exact incoming source hash.

## Confirmed customer-order comparison

1. Upload a fictional customer-order standard with a unique source file and known scope (for example, direct desktop seats) to **Reference**.
2. Upload a new order with matching applicability facts.
3. Open the queue item. Before confirmation the detail says **Comparison not run** and names the exact proposed standard.
4. Enter a reviewer name and why the reference applies, then choose **Confirm reference and compare**. The app records this confirmation separately and calls the customer-order comparator with the same reference ID and hash.
5. Inspect the source-anchored section observations, then record the human decision.

## Honest pending case

Upload an incoming agreement with no compatible Active standard, conflicting applicability cues, or missing context. It still appears in the queue. Open it to see why matching abstained, confirm that **Comparison not run** is explicit, and inspect/download the preserved original. Resolve its scope or register an appropriate standard before another review.

## Current limits

- The upload control accepts DOCX only. The intake and matching application boundary accepts the shared extracted-document record; PDF normalization remains in Issue #14.
- Customer-order comparison reports extracted section and text differences. It does not interpret quantities, fees, renewal terms or legal effect.
- A reviewer confirmation establishes only the comparison baseline. Every incoming contract still requires a human decision.
- Local reviewer labels are self-attested. This synthetic prototype is not a multi-user or production legal system.
- AI is optional and off by default. The intake path does not need a provider key or model call.
- The human creative acceptance checkpoint remains pending with the owner.
