# Select a reference and compare on upload

In the local/private synthetic workspace, register a fictional Legal reference on the References page. An upload of an existing research specimen deliberately creates a separate Active record; the research catalogue entry remains a research candidate. The upload accepts structurally complete NDAs with different clause headings from the legacy baseline.

In the review queue, choose **Compare against** before selecting an incoming DOCX. Choose an Active reference, enter a reviewer name and the reason it applies, then use **Add DOCX and compare**. The server verifies the exact reference ID and original SHA-256, the extracted agreement family, and required applicability facts. If the chosen reference is incompatible or the source is incomplete, it refuses the comparison. An eligible NDA or customer order is compared within the upload request; the separate reference confirmation and comparison remain attached to the exact incoming original across restart. The contract decision remains pending even if no differences are found.

The default **Suggest an Active reference** path keeps conservative matching: an unambiguous NDA may receive a provisional comparison on upload; customer orders need a person's reference confirmation before their comparison. A selection is bound to the incoming source. Re-uploading the same bytes does not silently switch that binding.

The public site is a read-only static demonstration and cannot upload documents. This change does not deploy a private host or import the full research corpus.

## First controlled examples

- Mutual NDA — Product Evaluation (UK): exact copy has zero reported differences. Evaluation NDA with longer retention produces source-linked findings.
- Customer Order — Reseller Desktop Licences: exact copy has zero reported differences. Desktop reseller seat increase produces two observations.

These are fictional synthetic examples, not approved real-world legal standards. The no-difference result means only that the supported deterministic checks found no textual/structural differences. A reviewer still needs to inspect the original and decide the contract.

The next corpus step is one or two independently checked exact-match incoming examples for each of the eight research reference variants, followed by changed-term and difficult cases. Keep the withheld answer key out of runtime inputs, run the three-document positive/abstain pilot and blinded matching check first, then expand toward 200–300 fictional incoming contracts in measured batches.
