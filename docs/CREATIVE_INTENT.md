# Chug — Creative intent

## The idea
**Simple on the surface. Exceptionally robust underneath.**

The aim is not to hide complexity behind a pretty interface. It is to understand the complexity, handle as much of it as software can reliably handle, and leave the user with a calm, natural and trustworthy experience.

The longer-term direction is to make a legal team's reviewed experience useful in later reviews through a governed, traceable learning loop. The present synthetic prototype records decisions and lets a demonstration reviewer explicitly publish a source-linked decision for later search, then withdraw it. Publication authority is self-attested and does not create organisational policy. See [Product direction](PRODUCT_DIRECTION.md) for the current boundary and proposed next stage.

A busy legal reviewer should not have to reconstruct an entire contract merely to find out what needs their judgement. Chug should do the mechanical work of extracting, comparing, organising, checking and retrieving relevant history, then make the important differences and their evidence easy to inspect.

**Product north star:** Make routine commercial contract review easier, safer and more consistent by bringing important differences, supporting evidence and relevant organisational experience together. Legal professionals retain judgement and authority. Deliberate feedback and governed reuse make the product more useful over time; AI is used only where it offers a worthwhile advantage over simpler methods.

This is a creativity demonstration: the distinctive idea is not “add AI to legal review”. It is **redesign the work so that routine effort falls away without losing assurance**.

## Design signature
- **Simple on the surface; robust underneath.** Complexity is acceptable internally only when it improves user simplicity, assurance or demonstrated business value.
- **Find the system behind the symptom.** The problem is not just reading documents; it is repeated decisions, scattered precedent, interruptions, bottlenecks and peak-time queues.
- **Rethink the workflow before automating it.** Do not digitise unnecessary steps or put AI on top of an incoherent process.
- **Do the tedious work; leave the judgement.** Software finds, compares, organises and explains. A legal reviewer decides.
- **Summary first; evidence always available.** The short view should be actionable, and every material claim inspectable against its source.
- **Safe shortcuts, never concealed gaps.** Fast review requires demonstrable document coverage, independent controls and explicit human confirmation.
- **Warm, frictionless interaction.** Use language a real reviewer would say; avoid unnecessary jargon, clicks and ceremony. Offer depth progressively.
- **Trust is designed in.** Separate source facts, historical decisions, deterministic findings, AI interpretations, uncertainty and reviewer conclusions.
- **AI must earn its place.** Prefer reliable conventional engineering; use real AI only for a task where its added value is credible and testable.

## The key user question
How can a busy legal team make proportionate, well-supported decisions without having to manually reread every clause in every routine contract?

Do **not** promise that a machine can guarantee legal correctness or detect every risk. Instead, make what was checked, what changed, what is uncertain and what needs attention unusually clear.

## Target experience
A reviewer opening a backlog should immediately see:
1. Which documents appear routine **candidates** for brief human confirmation.
2. Which contain substantive differences requiring judgement.
3. Which contain potential critical exceptions or incomplete analysis and need escalation.

Opening a contract should lead with: **what changed, why it may matter, relevant historical context, suggested next action**. Source excerpts, full original documents, comparison details and provenance remain one interaction away. The reviewer can inspect and override suggestions, with a reason recorded.

Illustrative queue counts, fictional contract names and sample findings are **design examples**, not tested product results.

## Under-the-hood assurance
Account for complete document content, including tables and schedules, or block shortcut routing; preserve original bytes and source anchors; compare against an approved reference; detect missing/added/changed material; check for cross-clause conflicts and known critical patterns independently; retrieve precedent with its context and status; validate AI-supported claims; record human decisions append-only.

The product cannot guarantee that all issues will be found. A quick-review route means the required checks completed within their stated scope, **not** that a contract has been proven safe or legally approved.

## Creativity without scope drift
The specification is a hypothesis to test, not an excuse for arbitrary feature additions. If a simpler or more effective workflow emerges, document it as a small reversible proposal with expected user benefit, risk, cost and test. Do not silently redesign core safety behaviour.

## Time horizon
Aim for a compelling, honest, well-engineered vertical slice in 2–3 days, not a production legal platform. Prefer one beautifully executed workflow over many shallow features. More time may be justified by user feedback or validation needs; do not claim production-grade legal accuracy.

## Demonstration narrative
We began with a legal team's workload, not a model. We questioned the workflow, used deterministic software for tasks it handles well, introduced genuine AI only where justified, and made complex assurance feel simple to the reviewer. Show this through the interaction, evidence and measured or explicitly hypothetical business impact.
