# CHUG — Start Here

**Capture. Hold. Use. Grow.**

*An enduring organisational knowledge foundation.*

Chug explores how organisations can preserve, connect and reuse knowledge created through everyday work, so that people can build on what their organisation already knows.

The first working experiment uses commercial contract review to explore this idea.

I've built a small prototype called Chug, using fictional contracts, to explore whether conventional software can make repetitive review work easier while preserving useful information and decisions for future use.

The prototype compares documents, highlights differences, retrieves relevant historical context and records human decisions. It also demonstrates how selected decisions can be deliberately shared for future reference or withdrawn.

The aim isn't to replace professional judgement. It's to reduce unnecessary effort, make important information easier to find and understand, and explore how today's work might help with tomorrow's decisions.

**This is a working experiment, not a validated legal product.**

## Choose how to explore

**Read-only web demonstration**

Explore the fictional contracts, review findings, supporting evidence and historical context without installing anything. Recording decisions and changing documents are not available in this version.

**Interactive local demonstration**

Run the application on your own computer to experience the fuller workflow, including uploading fictional documents, recording decisions and exploring how knowledge can be published, retrieved and withdrawn.

Both experiences use synthetic information. The local demonstration works without an AI subscription or external model.

Instructions for each experience follow below.

## Getting started

There are two ways to explore Chug.

### Option 1 — Explore online

The read-only demonstration lets you explore the contract-review experience directly in your browser at **[chug.smooks.co.uk](https://chug.smooks.co.uk)**.

Start on **Home**, where you'll find a queue of fictional contracts organised by the attention they may need.

Choose a contract to explore:

- What has changed from the reference document.
- Why those changes might matter.
- What the original documents and supporting evidence show.
- Whether similar wording has been reviewed before, and under what conditions.

The online demonstration does not save new decisions or accept document uploads.

### Option 2 — Run Chug locally

The interactive demonstration provides the fuller experience, including recording decisions and exploring how knowledge from one review can become useful in another.

Use Python 3.11 or 3.12 for the verified DOCX workflow. GitHub validation uses 3.11; the local setup was checked with 3.12. No additional Python packages, account or AI subscription are required for this workflow.

From the downloaded project's main folder, run:

```sh
python3 -m chug.server --port 8771
```

Open the following address in your browser:

`http://127.0.0.1:8771`

You can now explore the same fictional contracts, upload supported synthetic DOCX documents, record decisions and experiment with sharing and withdrawing previous decisions.

For the current automatic matching and human-review journey, follow [the five-case walkthrough](docs/OWNER_REVIEW.md). It creates exact and changed NDA/order examples plus an unresolved match in a separate local state folder. The basic server command above starts the six original examples; it does not seed those five new intakes. For manual upload steps, see [the intake walkthrough](docs/ISSUE_8_WALKTHROUGH.md).

Your local demonstration data is stored on your computer. The application does not send contracts to an AI provider unless you deliberately configure and invoke the optional AI feature.

**Please use fictional documents only.** This prototype is not designed for confidential or production information.

## Your first five minutes with Chug

You don't need to understand the technology to explore Chug.

Visit **https://chug.smooks.co.uk** and follow three fictional contract reviews to see how the experience works.

### 1. Start with the work

On **Home**, select **Start reviewing**.

You'll see contracts organised by the attention they may need, rather than simply presented as a list of documents.

The aim is to help a reviewer understand where to focus their attention.

### 2. Explore an important exception — Falcon Data

Open **Falcon Data**.

This contract contains wording that could grant much broader rights than the reference agreement intended.

Explore what Chug has identified, why it might matter and where the relevant wording appears in the original and reference documents.

Notice that Chug highlights the concern but leaves its interpretation and resolution to a person.

### 3. Explore a previous decision — Brookside AI

Open **Brookside AI**.

Here, Chug identifies a change to the contract's duration and brings a relevant previous decision into view.

Explore the reasoning and conditions attached to that earlier decision.

The important distinction is that a previous decision provides useful context. It does not automatically determine what should happen this time.

### 4. Explore a routine candidate — Birchbridge

Open **Birchbridge**.

This contract closely resembles the reference agreement.

Chug identifies it as a possible routine review, but it still requires a person to confirm that the agreement is appropriate.

A routine candidate is not an automatic approval.

### 5. Look beneath the summary

Return to any contract and explore the supporting evidence.

You can inspect the original wording, the reference document, previous review information and the checks performed.

The aim is to make complex information easier to navigate without removing the ability to examine it in detail.

**The idea to take away**

Chug is exploring two connected opportunities: making today's work easier and preserving useful knowledge so that tomorrow's work can benefit from it.

The online demonstration is read-only. The interactive local version also lets you record decisions and explore how knowledge can be deliberately shared, reused and withdrawn.

## How Chug builds on previous work

The contract-review demonstration is about more than comparing documents.

It's an opportunity to explore how knowledge created through everyday work can become useful when a similar situation arises in the future.

An earlier local learning experiment and its automated tests explore this process. The current automatic-upload workflow records assessments and contract decisions; connecting those new reviews to reusable previous decisions is the separate next milestone (#10). The sequence below describes that learning experiment, not the five-case upload walkthrough.

### Capture — A decision is made

Open the fictional **Maple Metrics (L01)** contract.

A reviewer encounters wording allowing certain records to be retained after the agreement ends.

The reviewer considers the wording, records a decision and explains the conditions under which the retained information may be acceptable.

Chug preserves the decision alongside its source evidence, reasoning and context.

### Hold — Preserve the knowledge

The reviewer can choose to share that decision as a precedent for future reference.

This is an explicit action. Recording a decision does not automatically make it approved organisational guidance.

The original evidence, rationale and limitations remain connected to the published record.

### Use — Find it when it's relevant

Now explore **Harbour Analytics (L02)**.

Chug can retrieve the earlier decision because the new contract contains potentially related wording.

But the circumstances differ.

The earlier decision concerned records retained for regulatory purposes. The new wording permits commercial analytics use.

Chug presents the previous experience as relevant context, not an answer that should automatically be applied.

A person must decide whether the distinction matters.

### Grow — Improve what the organisation can use

As further reviews take place, more decisions and their context may become available for future reference.

Information can also be corrected or withdrawn when it should no longer be relied upon.

The aim is to make accumulated experience more accessible and useful, while preserving its history and limitations.

This does not mean Chug automatically trains an AI model or turns individual decisions into organisational policy.

**Capture. Hold. Use. Grow.**

The longer-term question is whether this approach could help organisations retain and reuse valuable knowledge across many different activities, not just legal review.

## Trust, safeguards and limitations

Chug is designed to help people work with information more effectively, not to replace their expertise or judgement.

For that to be useful, people need to understand what Chug has identified, where the information came from, what remains uncertain and what they are responsible for deciding.

### What the prototype does to support trust

- **Source evidence:** Findings are linked to original documents and reference wording so people can inspect them.
- **Conservative recommendations:** Incomplete analysis or potentially important exceptions require further attention. A routine candidate is not an approval.
- **Previous decisions:** Historical experience is presented with its context and limitations, rather than automatically applied to a new situation.
- **Human authority:** People make and record decisions. Sharing a decision for future reuse requires a separate, explicit action.
- **Traceable history:** Recorded decisions, publications and withdrawals preserve a history of what happened.
- **Optional AI:** Conventional software supports the main workflow. AI is only introduced where it may provide additional value.

### What hasn't been established

This is an early prototype tested using fictional contracts.

It has not been validated by qualified legal professionals or tested within a real legal team's working environment.

The existing checks cannot guarantee that every legally important issue will be identified. We have not established measurable time savings, improved legal outcomes or the effectiveness of the optional AI integration.

The local prototype is not a secure, multi-user production system. It does not provide the access controls, privacy assurance or operational safeguards that would be necessary for real organisational information.

**Please do not upload real or confidential documents.**

### Keeping people at the centre

I also want to understand the wider consequences of introducing technology into people's work.

Reducing repetitive effort should create opportunities for people to concentrate on work that benefits from their expertise. It should not simply become a reason to increase workloads, reduce professional autonomy or introduce unnecessary monitoring.

The people using a system should be able to understand it, challenge it and influence how it develops.

**A useful system should make people more capable, not less important.**

These considerations will need to be tested and developed with the people who would actually use Chug.

## Status of the learning cycle

The repository includes fictional learning cases L01–L03 and a legacy decision/publication experiment. Its source-bound capture, explicit publication, retrieval and withdrawal mechanisms have automated tests:

```sh
python3 -m unittest tests.test_learning_loop -v
```

The current automatic-upload journey uses a different intake path. Its human assessments and contract actions persist, but the earlier L01/L02 instructions to upload, publish and retrieve through the browser are not a verified journey for that path. Connecting new uploaded reviews to relevant previous decisions is tracked as the next milestone in issue #10.

For the current demonstration, use [the five-case walkthrough](docs/OWNER_REVIEW.md). Treat the wider learning cycle as an experiment and future integration goal, not as completed acceptance of the new upload workflow.

## Technical reference and verification

Chug's current prototype is a small, locally runnable Python application with a browser-based interface.

It uses conventional software for document extraction, comparison, evidence tracking, review routing and historical retrieval.

The core demonstration works offline, without additional Python packages or AI credentials.

### Running the tests

From the project's main folder, run:

```sh
python3 -m unittest discover -s tests -v
python3 -m tests.evaluate
python3 -m tests.adversarial_audit
```

These checks cover the implemented functionality, the six original fictional NDA scenarios and additional adversarial cases designed to expose misleading or incomplete analysis.

For the browser-interface checks, Node.js is required:

```sh
node --check web/app.js
node --test tests/test_web_ui.mjs
```

These tests provide evidence about specific technical behaviours. They are not a substitute for practical user evaluation or qualified legal review.

### Keeping experiments separate

By default, local review decisions and uploaded demonstration files are stored in `.chug-data/`.

To start with a fresh set of fictional decisions, launch the application with a separate state directory:

```sh
python3 -m chug.server --port 8771 --state-dir ./chug-review-test
```

This keeps the new experiment separate from previous local review activity.

### Optional AI integration

Chug includes an optional OpenAI Responses API integration for explaining selected differences in contract wording.

It is disabled by default, requires explicit configuration and may incur API charges.

The deterministic review workflow does not depend on it.

Configuration and implementation details are described in [`docs/AI_ARCHITECTURE.md`](docs/AI_ARCHITECTURE.md) and [`docs/decisions/001-scoped-semantic-comparison.md`](docs/decisions/001-scoped-semantic-comparison.md).

Use fictional documents only.

### Technical boundaries

The prototype currently supports a limited family of synthetic DOCX agreements. It does not support every Word document structure or provide a general-purpose legal analysis service.

The wider knowledge foundation, cross-system integrations, production access controls and advanced retrieval capabilities remain areas for future exploration.

For more detail, see:

- [`docs/PRODUCT_DIRECTION.md`](docs/PRODUCT_DIRECTION.md) — the wider product vision.
- [`docs/AI_ARCHITECTURE.md`](docs/AI_ARCHITECTURE.md) — current AI capability and possible future architecture.
- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — functional requirements and implementation boundaries.
- [`docs/CREATIVE_INTENT.md`](docs/CREATIVE_INTENT.md) — experience and design principles.
- [`docs/ENGINEERING_PRINCIPLES.md`](docs/ENGINEERING_PRINCIPLES.md) — technical and evaluation principles.

The source code, tests and documentation are available in the project repository.

## Where Chug goes next

The commercial contract-review prototype is a starting point, not the intended limit of Chug.

What interests me is whether organisations can become better at preserving and using the knowledge they already create.

The next step is to explore that possibility with the people doing the work.

I want to understand their existing systems, processes and challenges, identify where useful knowledge already exists, and explore how making it easier to find and connect could help.

The approach is collaborative and iterative: understand the work, build something useful, test it together, learn and refine.

The eventual solution might involve a dedicated interface, improvements within existing systems, connections between them or carefully chosen AI capabilities.

I don't want to determine those answers in advance.

**The aim is to make today's work easier while allowing tomorrow's work to benefit from what the organisation has already learned.**

---

*Thank you for exploring with me,*

*Mooks*
