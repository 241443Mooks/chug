# Product scope

This describes the local synthetic prototype on main. The deployed public demo may be older. Implementation and test records take precedence over design intentions.

## Current workflow

1. Register fictional reference standards. Only active references with verified source files are eligible for automatic selection.
2. Upload supported DOCX contracts, singly or in batches of up to 20. Each gets its own result; repeated files retain their queue identity.
3. Extract source context and search for a compatible reference. Select only when a candidate stands ahead. Conflicting facts, insufficient context or no eligible reference leave comparison unrun, with a reason.
4. Compare supported NDAs or customer orders with the selected original. Keep the reference ID and hash with the result. Selection is provisional until a reviewer confirms applicability.
5. Show findings and supporting wording. NDA checks include selected patterns for missing protections and potentially conflicting terms. Customer-order comparison reports section and text differences; it does not interpret prices, quantities or legal effect.
6. Let a person assess each finding and record a separate contract action. Keep revisions and evidence rather than overwrite earlier records.
7. Retrieve related decisions through lexical matching. Sharing a decision for reuse and withdrawing it are explicit actions, separate from recording an outcome.

The public export contains read-only fictional snapshots and example review choices. It has no upload or save workflow.

## Review routes

| Code | Label | Meaning |
| --- | --- | --- |
| `routine_candidate` | Looks routine | Supported checks found no material difference requiring a stricter route; a person must still decide |
| `review_required` | Needs judgement | A change, uncertainty or unresolved reference needs review |
| `escalate` | Needs closer review | A selected check found potentially consequential wording or a missing protection |
| `blocked_extraction` | Analysis blocked | Required content could not be processed sufficiently |

Incomplete extraction or unrun comparison must be visible before decision controls. It must not produce a routine recommendation. Overall similarity must not suppress a flagged exception.

## Human actions and records

Finding assessments are **Not relevant**, **Acceptable**, **Problem**, **Needs further review** and **Deal breaker**. The last three require reasons.

**Accept contract** and **Flag for further review** are separate contract actions. A flag leaves review pending. Acceptance requires independent-original-review acknowledgement; unassessed or unresolved findings also require acknowledgement and a written explanation. Request amendment, Reject and Escalate are available as detailed outcomes.

Records retain incoming and reference identities, evidence snapshots, reviewer labels, timestamps and revision links. Local labels and publication roles are self-declared. An append-only application record is not proof against someone modifying local storage.

## Limits

- DOCX only in this version. Not all Word structures are supported; extraction can block review.
- Limited matching and comparison rules. No guarantee of legal completeness, equivalent meaning or safe-to-sign status.
- No verified organisational authority, production permissions, tenant isolation or operational security assurance. Fictional data only.
- No connected feed or built-in scheduler. The directory script needs a host-supplied schedule.
- No cross-system knowledge map, semantic search platform or automatic model training.
- No measured legal benefit, time saving or live AI improvement.

The tool must never approve a contract, accept risk, or make policy on a person's behalf. Recording a human decision does not transfer that responsibility to the tool.

[Run it](../START_HERE.md) · [Intake details](EXPLICIT_REFERENCE_UPLOAD.md) · [AI adapter](AI_ARCHITECTURE.md) · [Integration evidence](INTEGRATED_REVIEW_ACCEPTANCE.md)
