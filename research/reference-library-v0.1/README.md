# Chug — synthetic reference-library research (v0.1)

**Status: research fixtures, not supported by the running application, and not legally approved.**

This directory contains **8 synthetic reference documents and 4 incoming workflow fixtures**, along with a proposed dataset for exploring matching to an *applicable* reference, not merely the most textually similar one. It supplements GitHub issue [#16](https://github.com/241443Mooks/Swag/issues/16). The active registry reads only the eight records under `references/` and their `catalog.json` metadata; it does not load incoming fixtures or evaluation labels.

## Candidate standards

**NDA (3):**
- Mutual NDA — Product evaluation (UK) (`NDA-UK-EVAL`)
- Mutual NDA — Supplier assessment (UK) (`NDA-UK-SUPPLIER`)
- One-way NDA — Customer disclosures (UK) (`NDA-UK-ONEWAY`)

**Customer order (5):**
- Customer Order — Desktop user licences (direct) (`ORDER-PRO-DIRECT`)
- Customer Order — Managed cloud scanning (`ORDER-DAST-CLOUD`)
- Customer Order — Self-hosted scanning (`ORDER-DAST-SELF`)
- Customer Order — Desktop plus cloud bundle (`ORDER-COMBINED`)
- Customer Order — Reseller desktop licences (`ORDER-RESELLER`)

## Incoming workflow fixtures (4)

- `IN-01`: Evaluation NDA with longer, broader archival use
- `IN-02`: Managed cloud scanning order with a different hosting region
- `IN-03`: Desktop reseller seat increase
- `IN-04`: Reseller request for hosted/cloud scanning

These documents and their expected candidate labels are workflow/evaluation material, not a blind matching set. Expected labels are stored separately under `evaluation-only/expected-matches.json`; the application must not load that file, index it or send it to a model.

## Applicability before textual similarity

The controlled catalogue records reference ID, display name, family, variant, deployment, channel, disclosure direction, jurisdiction, a source-linked scope description, version, SHA-256 and explicit unapproved demo status. Missing source facts stay unspecified and appear as gaps; they are not inferred from document similarity.

Proposed processing sequence:
1. Retain original bytes and evidence anchors.
2. Identify family and transaction context from evidence; ask for missing facts.
3. Hard-exclude the wrong family, model, channel or direction.
4. Rank remaining candidates, showing reasons, gaps and uncertainty.
5. Escalate/abstain if no appropriate candidate exists.
6. Require an authorised reviewer to confirm applicability; immutably bind the chosen baseline version/hash to this review.
7. Compare exact wording, run independent safeguards and record the **human** legal decision.

AI may assist with classification, explanation or ranking but must not silently approve, publish standards or override a hard exclusion.

## Boundaries and caveats

- Inspired by common software-company transactions and public product categories only; **not PortSwigger's internal legal templates or approved policy**.
- All parties, prices and terms are invented for demonstration.
- These sources remain fictional research candidates, not approved legal wording or production policy. A proposed match requires human applicability confirmation before any comparison.
- Jurisdiction is not stated in the five customer-order sources. Their proposals therefore retain an explicit jurisdiction gap; do not present the records as jurisdictionally applicable.
- The active product does not yet compare customer orders or treat these standards as approved organizational guidance.
- Do not place these files into `dataset/reference/`, `dataset/incoming/` or runtime precedent search without separate architecture, legal, security and evaluation work.
- The 12 `.docx` documents under this folder are compact, regenerated Word specimens preserving the synthetic clause wording and key variations from the original starter set. **They are not byte-for-byte copies** of the separately supplied starter ZIP; formatting and ancillary metadata differ. Keep them research-only and revalidate them before test automation or legal review.

The key test is not merely finding something similar: it is **knowing when not to match**.
