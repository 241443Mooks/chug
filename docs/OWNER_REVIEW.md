# Chug — five-case owner review

Allow 20–25 minutes. Start with case 1; you can stop and send feedback at any point. This review checks whether the experience makes sense to you. You do not need legal expertise or to run the test suite.

Use the **local interactive version**. The public website cannot upload documents or save your review. The five cases below are genuine persisted intakes using fictional documents, not precomputed public snapshots.

## Prepare once

Use an updated local copy of main containing merged PR #37 (`477737d`), or this documentation branch. Run commands from the project folder containing `chug/`, `scripts/` and `START_HERE.md`. Use Python 3.11 or 3.12; CI uses 3.11 and this setup was checked locally with 3.12. No additional Python packages or AI account are needed for this DOCX journey.

Choose a fresh state folder outside the repo. The example uses a sibling folder; if it already contains previous review activity, choose another fresh name. Do not remove previous review data to reset this exercise.

```sh
python3 scripts/seed_synthetic_starter.py --state-dir ../chug-owner-review-2026-10-19
python3 -m chug.server --port 8771 --state-dir ../chug-owner-review-2026-10-19
```

Leave the terminal running. Open **http://127.0.0.1:8771/#queue** and select **All contracts**. You should see the existing six baseline contracts plus five new intake cases: **11 contracts total** in fresh state. The five new cases all start with human review pending. The two fictional standards are already registered for this exercise.

The seed script sends each incoming file through automatic selection/comparison without specifying a reference. Repeating the command preserves the same intake records; it does not clear assessments or decisions you subsequently save. For this review, no manual file selection is required. If you want to try uploading after the review, use **Upload DOCX contracts**; re-uploading these exact bytes should reopen the same review, not create another copy.

If the port is already in use, use `--port 8772` and open the same address with `8772` instead. If the seed command fails, stop and share the error text before reviewing.

## Review the five cases

Find each entry by name in the queue. Do not use the legacy Falcon/Birchbridge examples for this specific exercise.

| Case | Queue name | What should happen | Your task |
| --- | --- | --- | --- |
| 1 — Exact NDA | Incoming exact copy - Mutual NDA - Product Evaluation - UK - v0.1 | Chug selects the evaluation NDA reference and reports no differences. Human review remains pending. | Find which reference was used. Find both original downloads. Decide whether “no differences” is clearly separate from acceptance. Leave it pending. |
| 2 — Changed NDA | Incoming - Evaluation NDA with Longer Retention | Chug selects the same reference and reports four differences. | Find **Changed: Security and return**. Compare indefinite retention for research/product development with restricted legally required archives. Save **Problem** with a fictional reviewer label and a short reason. Then record **Flag for further review** for the contract. |
| 3 — Exact customer order | Incoming exact copy - Customer Order - Reseller Desktop Licences - v0.1 | Chug selects the reseller desktop reference and reports no differences. Human review remains pending. | Check that this is an order comparison against the order standard. Leave the contract pending. |
| 4 — Changed customer order | Incoming - Desktop Reseller Seat Increase | Chug selects the reseller desktop standard and compares immediately. Two differences are reported. | Find **Changed section: Order scope**. See **60** subscriptions in the incoming wording beside **25** in the reference. Check whether the comparison and human next step are understandable. |
| 5 — Unresolved match | Incoming - Ambiguous Reseller Cloud Scan Purchase | No suitable reference is selected. **Comparison not run** is explicit. | Find the reason and the exact original. Check that this cannot be mistaken for a completed, clear comparison. You can flag it if you wish; do not accept it for this exercise. |

The NDA's four differences include three specimen heading/record changes and one substantive archive change. The order's two differences include introductory text and seat scope. Counts describe textual differences, not the number of legal risks. Note whether those presentation differences distract you.

## The two actions in case 2

1. In **Review findings**, find the security/return finding. Choose **Problem**, enter a reason such as “Check the indefinite archive permission”, add a fictional reviewer label, and choose **Save assessment**.
2. Confirm that **Latest: problem** and a revision are shown. This is a finding assessment; it does not decide the whole contract.
3. In **Contract decision**, choose **Flag for further review**, add your label and reason, and choose **Record contract action**. A flag does not require you to claim that you have independently reviewed the original.
4. Open/read **Review history**. It should show the finding assessment and contract flag as different events. The contract remains pending/flagged.
5. Refresh the page. Your saved assessment and flag should remain visible. Return to the queue and reopen the same contract.

An applicability confirmation, if you choose to try it, records only that the selected reference applies. The automatic comparison already ran. Confirmation is separate from contract acceptance. Accepting a contract requires acknowledgement that you independently reviewed its exact incoming original; unresolved findings require an explanation and acknowledgement too. You do not need to test acceptance during this owner review.

## Send feedback in plain English

For any confusing or broken step, send:

> Case:  
> I tried to:  
> I expected:  
> What happened:  
> Does this prevent review, or is it a wording/layout improvement?

A screenshot is optional. You can also tell Codex what happened in ordinary language and ask it to record the note. Do not spend time diagnosing the code.

### Owner feedback record — pending

Only fill this from the owner's actual observations. Automated browser results do not count as owner acceptance.

| Case | Owner result: accepted / needs change / not reviewed | Note |
| --- | --- | --- |
| 1 — Exact NDA | Not reviewed | |
| 2 — Changed NDA and saved assessment/flag | Not reviewed | |
| 3 — Exact order | Not reviewed | |
| 4 — Changed order | Not reviewed | |
| 5 — Unresolved match | Not reviewed | |

Overall: **Owner acceptance pending.**

## Known boundaries

DOCX only for this session. PDF remains separate. There are three known unnecessary abstentions in other order variants; this five-case setup does not establish that all contracts match correctly. The answer-key-blinded check used an agent-authored key, not an independent human benchmark. See [the integration report](INTEGRATED_REVIEW_ACCEPTANCE.md) for technical evidence.

This current upload journey captures review decisions and finding evidence. Finding and publishing relevant decisions from newly uploaded contracts for later reuse is the separate next milestone #10. Do not use the old L01/L02 upload tutorial to assess this journey.

When finished, stop the server with **Ctrl+C**. Keep the sibling state folder so your feedback can be checked against the same saved reviews. Return to [today's plan](DAY_PLAN_2026-10-19.md) for block 3.
