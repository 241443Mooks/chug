# Chug — Experience principles and review journeys

## North star
**Simple on the surface. Exceptionally robust underneath.** Minimise user effort and cognitive load without concealing evidence, gaps or uncertainty.

## Interaction principles
1. **Start with the decision, not the machinery.** The queue answers “what needs attention?” A document view answers “what changed, why, what happened before, what next?”
2. **Progressive disclosure.** Present concise summaries first; keep source excerpts, original DOCX, complete comparison, analysis coverage and historical context easily accessible.
3. **Act where you are.** Confirm, refer, request amendment or record a reason from the relevant finding or document view. Avoid detours and duplicated entry.
4. **Use reviewer language.** Prefer plain, natural labels and concrete explanations over model jargon, unexplained scores and developer terminology.
5. **Make trust legible.** Clearly distinguish extracted facts, deterministic checks, AI interpretations, past decisions and human judgements. Every material finding has traceable evidence.
6. **Make uncertainty and incomplete coverage conspicuous.** No cheerful green state when extraction, source validation or required checks failed. State what remains unchecked.
7. **Optimise both novice and expert paths.** A new reviewer gets guidance and definitions; an experienced reviewer can move quickly without repeated prompts.
8. **Prioritise exceptions, not noise.** Group administrative changes, avoid repetitive findings, and make critical deviations hard to miss without alarm fatigue.
9. **Preserve control.** A reviewer can inspect the entire contract, disagree with suggestions and record the decision. No automatic legal approval.
10. **Earn each interaction.** Remove a click, field or screen if it does not help judgement, assurance or accountability.

## Minimum reviewer journeys
### A. Busy morning / peak queue
The reviewer sees a prioritised multi-document queue with understandable categories: potential escalation, needs judgement, routine candidate, and analysis blocked. Show why each item is in its category and what can be handled next. Avoid claiming actual queue volumes or time savings from fictional examples.

### B. Routine candidate
Show what was checked and what differences were considered administrative or non-substantive. Offer brief human confirmation **only if** required coverage and controls completed; keep full document accessible. Human confirmation is not automated approval.

### C. Substantive amendment
Show the changed wording alongside the reference and any relevant prior decision, including acceptance conditions or rejection. Make the next action easy; never infer blanket permission from precedent.

### D. Hidden critical clause
A mostly standard NDA contains a dangerous added provision in another clause or schedule. The interface elevates the exception, points to exact evidence and blocks the routine route regardless of overall similarity.

### E. Incomplete or failed analysis
A missing table, unsupported document content or unavailable required AI check must not look like a routine candidate. State the specific limitation and provide a safe manual review path.

## UX acceptance
- In a short walkthrough, a reviewer can identify the next priority, understand the issue, inspect original evidence and record a decision without hunting through unrelated screens.
- No material claim is a dead end: its source or limitation can be opened.
- Critical exceptions remain visible even in high-similarity documents.
- Error, empty, loading and offline states are informative, not falsely reassuring.
- A simplified surface must never conceal skipped checks.
- Test the actual UI journey, not just backend functions.

## Anti-patterns
Generic AI chat pasted onto a document viewer; opaque risk percentages; auto-approval; “all clear” without coverage; walls of legal text by default; overly elaborate dashboards; modal-heavy review flows; decorative metrics; model output without source anchors; and replacing a flawed process with a faster version of the same flawed process.
