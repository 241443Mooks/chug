# Decision 002 — Keep the working Legal pack separate from future workspaces

**Status:** accepted for the synthetic prototype; multi-workspace architecture remains a proposal.

## Problem and success criterion

The legal reviewer should reach the NDA queue immediately. A visitor should also understand how evidence-led review might apply elsewhere without mistaking a concept for a working or authorised product. A second contract family should have an identifiable place for its own rules before one is built.

## Boundary in the current code

| Layer | Current evidence | Authority and limit |
| --- | --- | --- |
| Shared application path | `chug/server.py`, `chug/document.py`, `chug/ledger.py`, `chug/corrections.py` preserve source bytes and hashes, evidence anchors, reference bindings, review events, publication and withdrawal. | Local synthetic single-reviewer workflow. DOCX extraction and some API/UI shape still assume the present legal demo; this is not a general workflow engine. |
| Active domain pack | `chug/nda_pack.py` supplies the bundled NDA library and source paths, supported reference rule, analysis, clause title, lexical correction terms, display name and route order. `chug/engine.py` contains the NDA comparison and indicators. `tests/test_nda_pack_boundary.py` proves the application calls the pack through a real review. | Only mutual NDAs are supported. A selected uploaded reference still needs the bundled clause headings and independent human validation. |
| Organisation workspace | The optional `#explore` page presents Legal as the sole working tile; `#home` and `#queue` are the daily route. | Other tiles are non-interactive product concepts. There are no other department workflows or datasets. |
| Role and permission boundary | Demo publisher identity is self-attested and visibly labelled. | Production tenant isolation, roles, access control, confidentiality, retention and department-scoped search **do not exist**. They must be designed and verified before real multi-department use. |
| Future ideas | Small customer order forms are a credible next Legal pack; other departments might use the evidence/decision pattern. | Neither has been implemented or validated. No existing Legal precedent may be interpreted as HR, finance or other-team guidance. |

The narrow pack seam is deliberate. The shared application asks a pack to validate a reference, analyse a document and supply its domain-specific labels and source paths. It does not load a dynamic plugin registry or promise that the existing DOCX and UI paths support arbitrary document types. A second pack would need its own reference selection, terminology, specialist data, comparison and safeguards, escalation rules, UI, fixtures and acceptance tests. Only then should the common interface be generalised further.

## Alternatives and decision

We considered a permanent organisation home page and a generic pack/plugin system. Both would add navigation or abstractions before a second working use case justifies them. The optional Explore page leaves the 100th legal review fast; the active NDA pack moves real rules out of the application without pretending the broader design is finished.

## Contribution and failure boundaries

Engineering can propose and test extraction/comparison changes; legal reviewers decide legal outcomes and authorised Legal guidance; future domain owners must validate their domain rules; security and privacy owners must approve real data and deployment boundaries. A reviewer correction is a feedback event, not policy. Published synthetic precedent remains scoped to this NDA workflow and cannot authorise another decision. Unsupported extraction blocks routine routing; missing department permissions block multi-department deployment rather than falling back to broad access.

## Verification and revisit

Run the full synthetic route evaluator, API tests and browser navigation from Home → Explore → Legal queue. Inspect both desktop and narrow layouts and confirm concept cards have no link, button or keyboard action. Revisit the interface only when an order-form pack or another domain has actual reference data, rules, evidence and independent evaluation. The optional AI adapter remains off by default; its benefit has not been established by a live comparison.
