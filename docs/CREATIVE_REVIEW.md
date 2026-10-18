# Chug — Human creative review checkpoint

This is a **human judgement gate**, separate from automated correctness tests. Codex must prepare evidence and proposals, not self-certify creative quality or silently expand scope.

## When
After a working end-to-end vertical slice and before final packaging. The reviewer may also use this checkpoint after seeing an early UI.

For this consolidation, open the local app using [START_HERE](../START_HERE.md#start-in-under-a-minute). Try the queue and T03 evidence journey, the Assurance summary, a routine candidate and the separate L01/L02 learning cycle. Judge whether the main journey makes sense without reading the technical documentation. The owner has not yet recorded an acceptance outcome.

## Questions
- Does this feel genuinely simpler than the original contract-review workflow, or have we just digitised its friction?
- Can a busy legal reviewer immediately see what needs attention and why?
- Is the underlying robustness real and inspectable, rather than a polished illusion?
- Are summary, original evidence, historical context and next action naturally connected?
- Have we eliminated avoidable clicks, jargon, repetition and unnecessary AI calls?
- Are we confident enough to offer a shortcut, and do we explicitly block it when we are not?
- Does the experience respect both a first-time reviewer and an expert?
- Does every added layer of complexity reduce user complexity, improve assurance or create demonstrable business value?
- What did we discover while building that challenges our original assumptions?
- Is this a distinctive, coherent product demonstration rather than a generic AI dashboard?

## Review outcome
Record one of: **accept experience**, **request a focused revision**, **defer an opportunity**, or **stop due to a trust/usability concern**. Note the observed evidence, impact and smallest useful next step. Do not claim the creator has approved the design until they have actually reviewed it.

## Discovery journal
Maintain short entries in `docs/DESIGN_JOURNAL.md` as meaningful discoveries arise:
- Observation or user friction
- Original assumption
- What changed in our understanding
- Options and trade-offs
- Decision or proposed experiment
- Evidence and remaining uncertainty

This journal is a record of thinking, not marketing copy. Keep it concise and honest.

## Scope control
Codex may propose reversible improvements with expected user value and tests. Changes to critical safeguards, major architecture, paid dependencies or sprint scope require explicit approval. Do not substitute visual polish for an incomplete core journey.
