# Public page language review

**Date:** 18 October 2026  
**Status:** Draft for owner review. This is a plain-language pass inspired by ASD-STE100. It is **not** certified ASD-STE100.

## Copy rules for Chug

1. **Start with the task.** Say what the user can see or do before explaining how the system works.
2. **Use one idea per sentence.** Keep sentences short. Prefer active voice and familiar words.
3. **Use the same terms on every page:** incoming contract, reference document, finding, review, decision, fictional example.
4. **Put the result first.** Show what Chug found, the source wording, what Chug could not confirm, and the next human step.
5. **State limits in plain language.** “Chug could not check this section” is clearer than “analysis coverage incomplete”.
6. **Keep proof accessible.** Do not remove source passages, file hashes, version/status, past-decision conditions, or uncertain matches. Put technical details behind clear headings.
7. **Do not overstate certainty.** “No matching clause found” is appropriate only if the check supports that claim. Otherwise say “No clear match found”.
8. **Separate the two products.** Public = read-only fictional examples. Local/private = uploads, new analysis and recorded reviewer decisions. Do not promise public actions that cannot work.
9. **Use normal UK English.** No marketing claims, management jargon, internal function names, or clever labels that need interpretation.

## Pages checked

| Page | Plain-language direction | Scope of this draft |
| --- | --- | --- |
| Home | Tell visitors to open a contract, inspect changes, then decide. | Updated |
| Review queue | Explain the labels and make the next click obvious. | Updated explanatory text; finding layout in #19 |
| Review overview | Show all findings together; say what needs checking. | Luna's #19; no competing code changes here |
| Compare wording / full document | Show original words and matched reference, and label missing/uncertain matches accurately. | Luna's #19; do not change legal source text |
| Checks and review history | Use “What Chug checked”, “Not reviewed yet” and direct status language. | Luna's #19 |
| Reference library | Explain what a reference is, where it came from and whether it can be used. | Updated |
| Help | Short steps, simple definitions, clear limits. | Rewritten |
| Explore Chug | Distinguish working tools from ideas. | Updated |
| Decision log | Lead with “fictional”, make search and filters easy to understand. | Updated |
| Loading / errors | Say what failed and what the user can do next. | Updated |

## Handoff notes for Issue #19

- **T05:** Show “4 things to check”. Do not hide three under “Other findings”.
- When a clause has no proven counterpart, say “No matching clause found”. When the match is uncertain, say “No clear match found”.
- Avoid “Independent whole-document indicator”, “Finding provenance”, and “Potential escalation indicators” in the primary interface.
- The public review must never say it saved a decision or provide an unusable decision form.
- Distinguish the two “Possible override or conflict” findings using the relevant section or wording.

## Before acceptance

- Read each page aloud. Remove sentences that need a second reading.
- Check the public site on desktop and mobile, including empty and failed-data states.
- Confirm that each rewritten description still matches the underlying check and its limitations.
- Keep fictional history separate from evidence. The 300 sample decisions remain unverified illustrations.
- Run the UI and Python tests. Test the live site **after** an approved merge and deployment.
