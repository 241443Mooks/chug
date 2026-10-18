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

You'll need Python 3.9 or newer. Install the pinned local PDF parser once; no account or AI subscription is required.

From the downloaded project's main folder, run:

```sh
python3 -m pip install -r requirements.txt
python3 -m chug.server --port 8771
```

Open the following address in your browser:

`http://127.0.0.1:8771`

You can now explore the same fictional contracts, upload supported synthetic DOCX or text-based PDF documents, record decisions and experiment with sharing and withdrawing previous decisions. PDF files are kept byte-for-byte; extracted evidence points to page and line anchors. Image-only, encrypted, malformed or layout-ambiguous PDFs are kept for inspection when intake permits, but are blocked from matching and analysis. The application does not verify electronic signatures.

For the new upload → matching → analysis → review queue flow, see [the Issue #8 walkthrough](docs/ISSUE_8_WALKTHROUGH.md).

### Try a fictional PDF

1. Open **References** and add a synthetic NDA PDF to the fictional Legal library. A supported text PDF can be used as an Active matching candidate; a person still confirms applicability before the review decision.
2. Choose **Check reference applicability** and upload a fictional incoming PDF. Inspect the proposed family and source excerpts; page anchors start with `pdf:p`.
3. Upload the same PDF through **Add DOCX or PDF** to create an incoming review. Open the queue item to inspect coverage, comparison evidence and the exact original download.
4. The public website remains read-only and does not accept uploads.

The parser limits uploads to 2 MB and 100 pages and blocks detected images, annotations, forms, optional-content layers, active content, table-like ambiguity and unreadable text. See [the PDF extraction decision](docs/decisions/003-pdf-text-extraction.md) for the remaining limits.

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

The interactive local version includes a small, fictional example of this process.

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

## Explore the interactive learning cycle

The local version of Chug lets you go beyond inspecting existing information. You can make fictional decisions, preserve their context and explore how they become useful during later work.

This short exercise demonstrates the process.

### 1. Review a contract

Start the local application using the instructions above.

Choose **Add DOCX** and upload `dataset/learning/L01-audit-retention.docx`.

Open the Maple Metrics review.

The contract contains a change concerning the retention of information after an agreement ends.

Inspect the original wording, the reference agreement and the concerns Chug has identified.

### 2. Record a decision

Choose **Record decision**.

Select the findings you've considered, enter a fictional reviewer name, choose an outcome and record your reasoning.

For this example, consider whether retaining records for a specific regulatory obligation, with access restricted to compliance purposes, might be acceptable.

The decision is preserved with its supporting evidence.

**Recording a decision does not automatically make it approved guidance for future work.**

### 3. Share the experience

Open the recorded decision in **Review history**.

Choose **Share this decision as a precedent**.

Confirm the source passage and record the context, conditions and limitations that someone would need to understand before considering this decision again.

Publication is deliberate, rather than automatic. The demonstration uses a self-declared reviewer role; it does not verify real organisational authority.

### 4. See what happens next

Upload `dataset/learning/L02-analytics-retention.docx` and open Harbour Analytics.

Chug can now retrieve the earlier decision as potentially relevant historical context.

But there's an important difference.

The earlier review concerned regulatory record retention. The new contract permits information to be retained for commercial analytics.

Explore how Chug presents that earlier experience without assuming the same decision applies.

### 5. Withdraw the precedent

Return to Maple Metrics and withdraw the published decision from its history.

Revisit Harbour Analytics.

The withdrawn decision should no longer appear as active published precedent, while the original publication and withdrawal remain recorded in the demonstration history.

### Explore further

You can also experiment with **Improve this comparison** to record a correction to how wording has been compared.

Corrections are separate from legal decisions. They can be deliberately shared for future retrieval, with their original context and limitations preserved.

The additional fictional contract `dataset/learning/L03-regulatory-records.docx` provides an opportunity to compare genuinely related wording with a misleadingly similar example.

**What this demonstrates**

A practical workflow can preserve more than its immediate outcome.

It can create a source-linked record of what happened, why a decision was made and under what conditions that experience might be useful again.

The experiment demonstrates a technical mechanism for knowledge reuse. It does not establish legal correctness, improved productivity or an automatically learning AI system.

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
