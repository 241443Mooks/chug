# Chug — Engineering, commercial and user-experience principles

## Governing principle
**AI must earn its place.** Start with the user problem and a conventional engineering baseline. Use AI only where a demonstrable benefit justifies its complexity, recurring cost, latency, privacy exposure and failure modes. This is an AI-focused application exercise, so demonstrate at least one **genuine, justified** AI capability; do not scatter AI across features simply to make the product look AI-powered.

## Three standards
### Engineering
- Choose the simplest reliable approach that satisfies the requirement; prefer deterministic code for hashes, parsing, structural differences, omissions, state transitions, queue ordering and audit records.
- Maintain source integrity, traceable findings, tests, observable errors, safe fallbacks and reproducible local setup.
- Evaluate alternatives before introducing frameworks, databases, embeddings, LLM calls or external services.
- Do not overengineer a synthetic-data prototype or confuse impressive architecture with product quality.

### Business case
For each major feature document: the user problem, existing solution/baseline, expected value, build/maintenance burden, per-document operating cost, latency, risk, and how improvement will be measured. Distinguish assumptions and estimates from observed results. Do not claim time savings without measuring them.

### User experience
- Optimize for a small legal team dealing with recurring redlines and peak-time queues.
- Prioritize what changed, why it matters, relevant historical context, source evidence and next action.
- Reduce unnecessary clicks and cognitive load; make full originals and uncertainty accessible.
- Make AI provenance visible when material, but avoid making reviewers operate the underlying technology.
- Human legal authority and clear escalation remain mandatory.

## Capability decision rule
1. Define the task and acceptance criteria.
2. Identify a conventional baseline, including established libraries/search techniques.
3. Measure or credibly evaluate quality, latency, cost, privacy and operational complexity.
4. Choose conventional software when it meets the need as well or better.
5. Introduce AI only when it offers a meaningful, testable advantage; document the rationale and fallback.
6. Revisit the decision when evidence changes.

## Initial allocation (hypotheses, not dogma)
| Task | Starting point | AI only if justified |
|---|---|---|
| DOCX extraction, hashing, structural accounting | Conventional code | Not needed for normal supported DOCX |
| Exact textual and clause differences | Conventional diff/alignment | For semantic ambiguity beyond lexical methods |
| Missing clause checks | Structural comparison | Not as sole detector |
| Historical decisions and audit trail | Database/files and deterministic rules | Not needed for storage or permissions |
| Precedent lookup | Keyword/metadata baseline, optionally hybrid retrieval | If semantic retrieval demonstrably improves relevance |
| Paraphrase interpretation and complex explanation | Compare deterministic/lexical baseline against real model | Strong candidate for a limited real AI feature |
| Queue ordering and workflow | Deterministic priority and reviewer state | Not needed by default |
| Final approval | Human reviewer | Never delegated |

## Proof, not theatre
- No simulated AI labelled as real AI.
- No scripted answers masquerading as general semantic understanding.
- No hidden test oracle access or test-specific routing.
- No invented legal conclusions, measured savings, cost numbers or accuracy claims.
- Live model integration is valuable only if it performs a well-defined task better than the baseline under a bounded cost and failure model.
- Keep a clear account of what the product can do without AI and what additional value the real model supplies.

## Required design decisions
Before implementing each significant AI-assisted feature, record a short architecture decision in `docs/decisions/`: problem, options, baseline, expected benefit, risks, cost/latency assumptions, selection, verification plan, and fallback. Decisions can be revised as tests reveal evidence.

## Submission story
Show that Chug began with the legal team's workload and risk, not with a model. Explain why conventional software carries the current journey and where the optional real-model adapter might add value. Demonstrate observed outcomes, distinguish mocked tests from live provider evidence, and state limitations plainly.
