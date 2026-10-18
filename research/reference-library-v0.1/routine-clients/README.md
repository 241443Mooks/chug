# Routine-looking synthetic client contracts (20)

**Research fixtures only. Not included in the active Chug application and not approved legal documents.**

These 20 client examples span the 8 fictional reference variants in the parent folder:

- 3 × mutual NDA — product evaluation
- 3 × mutual NDA — supplier assessment
- 2 × one-way NDA — customer disclosure
- 3 × direct desktop user orders
- 3 × managed-cloud scanning orders
- 2 × self-hosted scanning orders
- 2 × combined desktop/cloud orders
- 2 × reseller desktop orders

Each has a **fictional client identity and ordinary transaction description**. The proposed routine outcome means no deliberately modified material obligations relative to the respective research standard. This is an **authored expectation**, not a validated legal result. Parties, authority, dates, pricing, renewal, quantities, schedule availability, product/deployment and actual companion terms still require checks. A routine-looking document is **never automatic approval**.

### How to use

For now, browse these DOCX files separately from the live NDA demo. Do **not** put them into `dataset/incoming` or claim that the current NDA engine can compare sales orders.

The expected mappings for future tests are under `evaluation-only/expected-matches.json`. **Never give that file to runtime reference matching, models, embeddings, or test-time prompts.**

**Fixture-quality limitation:** These first-pass specimens deliberately include a `Proposed reference` identifier in their internal document metadata (the DOCX header paragraphs), inherited from the data-generation brief. That makes them useful for document loading, UX and comparison plumbing, but **unsuitable for blind reference-selection accuracy testing**. Before evaluating ranking or AI matching, generate an independently blinded set with those identifiers removed and use only the separate expectation file for scoring. Do not claim success by matching to a visible answer. Document filenames here omit reference identifiers to support a human-friendly display.

No real contracts, customer data or internal PortSwigger documents are used. Related: issue #16.
