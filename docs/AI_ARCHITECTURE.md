# Implementation and optional AI

## Current implementation

A local Python service serves the browser interface. Ordinary code handles supported DOCX extraction, hashes, reference selection, comparison, review routes, lexical history retrieval and decision records. The core workflow runs without external services or AI credentials.

- `chug/document.py`: extraction and source anchors.
- `chug/reference_registry.py`: references, context and matching.
- `chug/engine.py` and `chug/customer_order_review.py`: NDA and customer-order comparison.
- `chug/ledger.py` and `chug/corrections.py`: decisions, corrections, publication and withdrawal.
- `chug/server.py`: local API and workflow integration.
- `web/`: browser interface and read-only public export.

The local app stores original files and review evidence. It is not the proposed cross-system knowledge map. Production permissions and verified reviewer authority are absent.

## Optional clause explanation

`chug/ai.py` can call the OpenAI Responses API to explain a selected changed passage against reference wording. It is off by default and requires an explicit action, credentials and positive call/input/output limits. Selected synthetic source and reference passages are sent to the provider; charges may apply.

Configuration uses `CHUG_AI_ENABLED`, `OPENAI_API_KEY`, `CHUG_AI_MODEL`, `CHUG_AI_SESSION_CAP`, `CHUG_AI_DOCUMENT_CAP`, `CHUG_AI_MAX_OUTPUT_TOKENS` and `CHUG_AI_MAX_INPUT_CHARS`. See [decision 001](decisions/001-scoped-semantic-comparison.md) and the adapter for the configuration contract.

The adapter requests structured output and validates its shape and source anchors. Those checks cannot establish that the explanation is correct. Invalid or unavailable responses must show as failed or not run.

The model cannot change the review route, repair missing extraction, approve contracts or publish guidance. A failed call leaves the changed wording for human review.

Mocked tests cover integration and failure handling. No live provider evaluation or measured improvement over the non-AI comparison has been established. The ordinary comparison already detects the change; the question is whether an explanation helps enough to justify its errors, latency and cost.

## Possible later work

Better retrieval or links between records may prove useful. Start with source IDs, context and ordinary search. Test semantic search or source-based AI answers only against a specific unmet need.

Any cross-system links would need current source permissions, version checks, correction and withdrawal. A suggested relationship must remain distinguishable from an established fact. Saving a decision or updating a search index does not train a model or create policy.

[Product direction](PRODUCT_DIRECTION.md) · [Current scope](PRODUCT_SPEC.md) · [Test evidence](INTEGRATED_REVIEW_ACCEPTANCE.md)
