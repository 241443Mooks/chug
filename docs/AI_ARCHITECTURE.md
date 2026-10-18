# CHUG — Knowledge and AI Architecture

This document describes the knowledge foundation I want to explore, the technical capabilities already demonstrated in Chug's synthetic legal-review prototype, and the ideas that still need to be tested. It is not a claim that the wider architecture has been built.

## Starting with what Chug needs to know

I don't want to begin by deciding that Chug needs a particular AI model, database or interface.

I want to begin by understanding what an organisation already knows, where that knowledge exists, how it relates to other things, and when it could help someone with their work.

Five simple questions provide a starting point:

- **Who?** The people or roles involved, including contributors, owners, reviewers and those permitted to access the information.
- **What?** The relevant document, record, event, decision, outcome or relationship. These are different kinds of information and should not be treated as interchangeable.
- **Where?** The system responsible for the original information and a reliable way to locate the relevant record or passage.
- **When?** When something happened, was recorded or changed; which version applied; and whether it remains current.
- **Why?** The recorded reason, conditions or context that may explain an action or make information relevant to another task.

The value is not in creating five fields that someone must complete. It is in discovering and preserving the connections between answers that may already exist across organisational systems.

Sometimes an answer will be missing or uncertain. Chug should preserve that uncertainty rather than invent an explanation or require someone to create extra administration simply to fill a gap.

A recorded fact, a human explanation, a possible relationship and approved organisational guidance must remain distinguishable. The same applies to an established connection and a suggestion that two things might be relevant to one another.

Conventional identifiers, references and rules are the starting point. AI might later help find less obvious connections or maintain references, but those possibilities need to earn their place.

**The first architectural question isn't what AI can do. It's what Chug needs to know, how reliably it knows it and how that knowledge can help someone with their work.**

## What Chug actually holds

I don't envisage Chug collecting copies of everything an organisation knows.

Most information should remain in the systems responsible for it. Chug's role is to maintain a useful, reliable map of that information and the connections between it.

That may mean retaining:

- **References:** Which system holds something, its record identifier and how to locate it again.
- **Context:** What the information concerns and which people, activities or processes it relates to.
- **Relationships:** How one record, event, decision or piece of information connects to another.
- **History:** What happened, when it happened and how information or relationships have changed.
- **Status and authority:** Whether something is an observation, a recorded decision, a proposed connection or approved organisational guidance.

These are possible elements of the knowledge map, not a requirement to create five new records every time someone does something.

Where reliable identifiers or relationships already exist, Chug should reuse them.

Where information is missing, it may be possible to discover it through existing systems, straightforward rules or, where justified, AI-assisted methods.

Where a connection is suggested rather than established, that distinction should remain visible.

### Keeping the map accurate

A reference that was correct yesterday may not remain correct tomorrow.

Records may be moved, updated, superseded or deleted. People's responsibilities and access permissions may also change.

I want to explore how Chug can recognise those changes, maintain reliable references and avoid presenting outdated or inaccessible information as current.

Some updates may be possible through existing system events or conventional automation. Others may require validation by the appropriate people.

The aim is not to copy or control the organisation's information, but to maintain a trustworthy understanding of where it is and how it connects.

**Chug should remember the path to knowledge, the relationships that give it context and the limits of what it knows.**

## What the prototype demonstrates today

Chug's first bounded experiment is commercial contract review, using fictional documents. It explores whether reviewing an incoming contract can both make an immediate task easier and leave useful evidence and decisions available for future work.

The working local prototype uses conventional software to:

- Extract supported DOCX content, preserve originals and hashes, and provide source-linked evidence.
- Compare incoming mutual NDAs against the reference bound to their review, flag textual or structural changes and omissions, and run independent pattern-based checks.
- Route findings conservatively for human attention. A *routine candidate* is not an approval.
- Retrieve potentially relevant historical context through lexical matching, while keeping its conditions and limits visible.
- Record human decisions and corrections; explicitly publish or withdraw limited demonstration precedents.

These are technical behaviours in a synthetic local application, not proof of legal accuracy or real-world time savings. Demonstration publication authority is self-attested, not an actual organisational permission system.

The reference research registry and context-matching work are separate from a fully integrated multi-reference reviewer experience. Customer-order comparison remains backend-only and is not presented as a working customer-order review journey.

The publicly packaged Cloudflare experience is read-only. The local Python service is required for state-changing workflows such as uploading, recording decisions and publishing or withdrawing precedents.

The wider cross-system knowledge map described above **does not yet exist**. The present experiment demonstrates some of the evidence, decision and reuse mechanisms from which it might develop.

## The optional AI capability — implemented, not validated

The current AI integration in [`chug/ai.py`](../chug/ai.py) uses the OpenAI Responses API for one limited task: explaining the *possible effect and uncertainty* of a selected changed clause in relation to its reference wording.

It is disabled by default. A local operator must explicitly enable it, supply credentials and configure call, input and output limits. The analysis is an explicit action on selected synthetic material, not part of routine automatic routing.

The adapter sends only the selected source and reference passages for that comparison, treats contract text as untrusted input, requests structured output, checks the returned shape and source anchors, and identifies completed provider results. An unavailable or invalid response must not be mistaken for a successful check.

The model cannot approve contracts, override a review route, repair incomplete extraction, authorise precedent publication or establish organisational policy. It is neither a whole-document legal reasoning system nor a required safeguard.

Mocked tests exercise the integration and error handling. **No live paid provider call or measured improvement over the deterministic baseline has been established here.** The baseline already identifies changed passages and routes them to a person; whether AI interpretation offers worthwhile additional help remains unknown.

This integration is an early experiment in how AI might help people interpret information. It does not define or limit the AI capabilities that might eventually support Chug's wider knowledge foundation.

## Potential future architecture — hypotheses, not commitments

The next architectural question is how to make the knowledge map useful inside real work, with the smallest reliable implementation.

The foundation could support several complementary capabilities, developed and combined according to the needs of the organisation:

1. **Observe and capture:** Use existing records and system events to identify what happened, without unnecessary duplication.
2. **Locate and connect:** Maintain stable source references and relevant, attributable relationships; identify stale or unresolved links.
3. **Validate and govern:** Keep observations, suggested relationships, human decisions and approved guidance separate. Make correction, withdrawal and supersession possible.
4. **Retrieve at the point of need:** Start with identifiers, rules, metadata and lexical search. Test semantic or hybrid retrieval if users cannot reliably find what matters.
5. **Explain when helpful:** Consider source-grounded AI assistance to make relevant information easier to interpret, always with visible evidence and uncertainty.
6. **Learn through feedback:** Record whether the information was relevant, what people decided and what could improve; evaluate changes before adopting them.

Retrieval-augmented generation (RAG) might allow an AI model to answer a narrow question using selected, permission-appropriate source evidence. A graph representation might help describe and navigate typed relationships between records, people, events and decisions. Neither requires that Chug start with a vector database or graph database, and neither is currently implemented as the wider knowledge foundation.

**Recording a new event, refreshing an index or relationship map, and training or fine-tuning a model are three different operations.** More records do not mean a model has learned. Nor does a previous decision become an authorised rule simply because it can be retrieved.

Technology choices should follow observed retrieval needs, the organisation's existing systems and evidence that an approach is more useful than a simpler alternative.

## Trust, privacy and human authority

A useful connection is not necessarily a reliable conclusion.

Every material item presented by Chug should make it possible to distinguish its source, time or version, context, current status, uncertainty and authority. If information cannot be accessed, verified or shown to be current, Chug should not quietly present it as dependable.

The proposed cross-system foundation would need to respect source-system permissions, confidentiality, retention, deletion, changes of role and the sensitivity of the relationship map itself. Its design should minimise unnecessary copies and avoid turning metadata access into a way around existing restrictions. These are requirements to investigate and implement before real organisational use, not production controls already delivered by the prototype.

A recorded decision is evidence of what someone decided in a particular context. It is not automatically precedent, policy or approval for a later case. Authorised people must control any promotion to guidance, and be able to correct, withdraw or supersede it.

AI-generated explanations or suggested links must remain identifiable as suggestions. A human retains responsibility for interpreting evidence and deciding what to do.

Where information or relationships are corrected, superseded or withdrawn, Chug should preserve an appropriate record of those changes, including their source, timing and reason where known. Historical information should remain distinguishable from what is currently valid or authorised, subject to applicable retention and deletion requirements.

## How I would evaluate AI and the foundation

I would start with the team's existing workflow, establish what happens and how often, and agree what improvement should look like.

For any proposed AI feature, I would compare it with a conventional baseline using the same tasks and evidence. That comparison should examine relevance, factual support, uncertainty, avoidable errors, reviewer effort, latency, cost, privacy exposure and maintenance burden.

For the optional clause explanation, a separately agreed synthetic test set and qualified legal reviewers would be needed before making claims about legal usefulness. Any authorised live provider evaluation should record the configuration, output, failures, time and cost. An invented effect or misleading confidence is a serious negative outcome, even when the explanation sounds convincing.

For the wider knowledge foundation, I would ask whether people can find the right information sooner, reach its original source, understand why it matters, challenge incorrect connections and reuse previous experience without added administration. I would also look for unintended work created elsewhere.

I want to work collaboratively with the people who understand the work and the engineers who understand the technical possibilities. Start small, build something useful, test it together, learn from what works and what doesn't, then refine it. Repeat until there is clear evidence that the capability is helpful, trustworthy and worth maintaining.

If AI does not improve the experience enough to justify its cost, complexity and risk, it should not be added.

**Progress means making today's work easier while making the organisation's knowledge more useful for tomorrow.**

## Submission and evidence boundary

The runnable prototype is designed to work offline without AI credentials. The optional provider path is available only when deliberately configured; no key, confidential contract, live-model result or unverified value claim belongs in the submission.

The demonstration remains a synthetic proof of concept. Owner creative acceptance, qualified legal validation, measured benefits and final clean-tree ZIP verification are separate outstanding tasks. None can be inferred merely from the architecture.

Related evidence: [`START_HERE.md`](../START_HERE.md), [`docs/PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md), [Issue #30](https://github.com/241443Mooks/Swag/issues/30), [Issue #13](https://github.com/241443Mooks/Swag/issues/13), [Issue #14](https://github.com/241443Mooks/Swag/issues/14), [Issue #21](https://github.com/241443Mooks/Swag/issues/21).

**The architecture is not the destination.**

I want to establish a reliable foundation that allows an organisation to build on what it already knows, make that knowledge useful in everyday work, and develop new capabilities as genuine needs emerge.

The technology can evolve. The measure of success is whether people can work more effectively, make informed decisions and benefit from the knowledge their organisation has already created.
