# Swig — Design journal

Record meaningful discoveries, decisions and surprises as the product is built. Separate observations from hypotheses; do not fabricate user research, performance or results.

## Entry 001 — Starting design conviction
**Observation:** A small legal team repeatedly reviews mostly standard contracts, while changes and precedents recur and peak periods create queues.

**Hypothesis:** The largest benefit may come from reorganising review around exceptions and prior context, rather than automating full-document reading or adding AI to every step.

**Design direction:** Simple on the surface; exceptionally robust underneath. Deterministic extraction, coverage, comparison and workflow; real AI only where a conventional baseline is insufficient; human legal judgement preserved.

**What to validate:** Can a reviewer rapidly identify what needs attention, inspect its evidence and act without rereading everything? Are shortcut conditions sufficiently reliable and transparent? Which semantic task actually benefits from AI?

**Status:** Hypothesis — not validated with legal-team users.

## Entry 002 — Unsectioned text is a route blocker

**Observation:** An adversarial test placed text after the signature block. The parser extracted it, but the first comparison omitted it and offered a routine route.

**Decision:** Inventory every non-administrative body paragraph, including text outside numbered sections, as a difference. Treat signatures and metadata as administrative only when they match a constrained structure. Similarly, normalise only the party names in clause 1, while comparing the purpose wording. This preserves the simple reviewer surface without concealing unclassified content.

**Evidence:** Adversarial regression tests now require review for trailing instructions and changed purpose wording. This is a limited NDA-family rule, not a claim of general legal-document coverage.

## Entry 003 — The queue needs counterparties, not fixture filenames

**Observation:** Raw fixture slugs made the first browser view feel like a test harness rather than a legal team's queue.

**Decision:** Display the counterparty extracted from the parties clause, retaining the filename and hash in the document view. This reduces scanning effort without changing source identity or routing.

**Status:** Browser checked at desktop and 390 px. Human creative acceptance remains pending.

## Entry 004 — Extraction coverage did not imply review coverage

**Observation:** The first adversarial run offered a routine route when a consequential provision was added in a header or footer. Both parts had been extracted, but neither comparison nor the independent indicator scan examined them. Hidden or struck protection and duplicate ZIP parts produced similarly unjustified routine routes.

**Decision:** Treat extraction, comparison and independent safeguards as separate evidence-bearing checks. Compare all extracted non-body parts, scan all passages, block ambiguous or visibility-altered content, and show each check's status in a short Assurance view. A human still makes the legal decision.

**Evidence and trade-off:** The fixed synthetic challenge set moved from six false routine recommendations to zero. Two critical grants now escalate above the prewritten review target, and general DOCX visual fidelity is still unverified. The [audit](MISSED_EXCEPTION_AUDIT.md) preserves both the original misses and current limitations.

## Entry 005 — A blocked route needs blocked-state language everywhere

**Observation:** Browser QA of a hidden-text challenge showed “Analysis blocked” in the route, while the overview fallback still said no material wording change was found. That mixed message could invite a shortcut despite incomplete checks.

**Decision:** The blocked overview now says extraction is incomplete, comparison and safeguards were not run, and no clause conclusion is available. The Assurance tab repeats the specific extraction issue and leaves potential indicators “not assessed”.

**Evidence:** Reloaded browser view of uploaded A03 showed the corrected notice, blocked extraction, `not run` comparison/indicators and the `vanish` source location. Human legal review remains necessary.

## Entry 006 — A decision log is not a learning loop

**Observation:** The local ledger retains new human decisions, but precedent retrieval reads only the fixed historical library. A recorded decision is therefore visible as history without becoming reusable search context or organisational guidance.

**Direction:** Frame the product around governed reuse of reviewed experience. A decision must be assessed for context, conditions and authority before publication as a precedent; playbook guidance needs a separate approval process. Preserve the distinction in the submission narrative and do not describe the current prototype as self-learning.

**Status at `55882e7`:** Product direction recorded in [Product direction](PRODUCT_DIRECTION.md); promotion, playbook governance and improvement from corrections were then unimplemented. Entry 007 records the subsequent synthetic promotion slice.

## Entry 007 — Reuse needs its own event and the same retrieval path

**Observation:** A human decision and permission to show it in later reviews are different acts. Loading every ledger decision into precedent search would give an unreviewed case more authority than its evidence supports.

**Decision:** Keep decision events and explicit publication/withdrawal events distinct, with the publication tied to a considered source passage and contextual limits. Search historical and newly published cases through one lexical ranker; leave review routing independent. The local publisher role is self-attested and visibly labelled as demonstration-only.

**Evidence and limit:** The L01/L02 HTTP lifecycle and browser walkthrough show that publication makes a case retrievable and withdrawal removes it, while L02 still needs human judgement. This proves the interaction and state boundary, not legal applicability, secure authorisation or improved retrieval quality. See [feature evidence](LEARNING_LOOP_STATUS.md).

## Entry 008 — A reference choice must bind the review, not just the current screen

**Observation:** Choosing a different baseline for future uploads is useful, but a global reference switch could silently change an earlier finding or make an earlier human decision look as though it considered a different document.

**Decision:** Bind every uploaded analysis and decision to the exact reference SHA-256 at intake. Persist reference originals separately; reject incomplete or differently structured baselines within this NDA-family slice. Show the chosen reference in each review and allow the bundled sample to be selected again.

**Evidence and limit:** Restart, duplicate binding, tamper and custom-reference comparison tests pass. This is deliberately limited to the existing mutual NDA heading family; it does not perform concept-level alignment of arbitrary legal templates.

## Entry 009 — A correction teaches a question before it teaches an answer

**Observation:** A past correction to archive wording can be relevant to both a similarly restricted archive and a superficially similar commercial-use archive. A simple lexical match cannot establish that the same legal effect or acceptance applies.

**Decision:** Keep comparison corrections separate from contract decisions and non-reusable until an explicit demo publication. Retrieval shows the past source, reviewer explanation, context, limits and an unverified-applicability label beside the current finding. It never edits the deterministic comparison or route.

**Evidence and limit:** L01 → L03 / L02 tests show the authorised lesson appears for both, while both retain `review_required`; withdrawal removes active retrieval. This demonstrates governed organisational memory and the need for a reviewer to inspect the differing context. A genuine semantic improvement remains to be measured, not presumed.

## Entry 010 — The reviewer must be able to challenge an empty finding list

**Observation:** A correction control attached only to an existing finding cannot capture the most concerning feedback: the reviewer sees a provision Swig missed entirely. Leaving the route as routine after that report would misrepresent the known uncertainty.

**Decision:** Offer a collapsed “Something Swig missed?” control on every completely extracted review. Require an exact incoming or reference passage and explanation. Record the challenge as a comparison event with no invented system finding, and lift a routine candidate to human review while the challenge remains in the audit history.

**Evidence:** A synthetic T01 test begins with zero findings and a routine route, records a source-linked missed-provision report, then verifies `review_required` persists after restart. This is a reviewer signal, not a claim that the reported issue is legally material.

## Entry 011 — Show the extension idea without making it the daily workspace

**Observation:** A permanent organisation map would make every Legal reviewer navigate an unbuilt product on each visit. The existing server also kept NDA reference and comparison policy inside the application.

**Decision:** Put one optional Explore page behind a quiet Home link. Keep Legal as its only actionable tile, with other teams described as concepts. Move actual NDA policy and source-path choices behind a small pack boundary while leaving persistence and source identity in the application. Do not add speculative permissions or a pack registry.

**Evidence and limit:** The pack-boundary test and six-route evaluator exercise the existing Legal path. Browser navigation and responsive inspection are recorded in the Issue #10 status. A second pack, organisational isolation and usefulness of the Explore page remain unvalidated; creative acceptance is pending.
## Entry 012 — One name through the local demo (13 October 2026)

**Observation:** The reviewer-facing name and the launch command used different product names, making a simple user-test handoff confusing.

**Decision:** Use Chug consistently for the interface, Python package, optional AI settings and default local state path. Keep older dated test records and working GitHub links as historical identifiers. The local rename changes no review policy or safety route; the renamed app passed the existing tests and rendered smoke check. The repository slug still requires a separate GitHub rename.

## Entry 013 — Show the decision and its evidence before the machinery

**Observation:** In the owner's first Home and Falcon walkthrough, useful controls competed for attention. The Home counts did not route work, and the decision action was hard to find. Technical identifiers and multiple tabs appeared before the incoming/reference contrast.

**Decision:** Home now starts with the next action and live, clickable counts for pending work. A contract opens with one concern, its qualified reason, exact incoming wording and applicable reference wording, followed by other material findings and specialist tools. The human decision action is visible immediately. Source identifiers, hashes and original files remain in Document details.

**Discovery:** Falcon's leading whole-document indicator has no direct comparison pair in the engine, but its related no-licence passage exactly matches the selected reference. Showing that exact reference protection beside the added wording makes the relationship legible without inventing a changed clause. When no exact reference passage is available, the UI says so rather than implying a match.

**Evidence and uncertainty:** Browser checks covered filtered queues, Falcon source navigation, a synthetic decision and refresh, desktop and narrow layouts. They verify UI behaviour in a local demonstration, not reviewer understanding or legal interpretation. Owner creative acceptance remains pending under #13; broader families and incoming feeds remain discovery under #16.

## Entry 014 — A close textual match is not enough to choose a standard

**Observation:** The research library had eight differently scoped references, but its catalogue also mixed reference metadata with expected candidates for evaluation inputs. Several order sources do not state a jurisdiction, and NDA scope depends on whether disclosure is mutual and why the parties are exchanging information.

**Decision:** Keep the runtime registry limited to hash-verified reference sources. Move expected labels into an evaluation-only file, extract contextual facts from exact source passages, hard-exclude known conflicts, and abstain or expose a gap where context is missing. Treat every result as an unapproved research candidate that a human must validate before comparison.

**Evidence and uncertainty:** Independent synthetic tests cover mutual and one-way NDA context, supplier and product-evaluation purpose, direct cloud orders, reseller/cloud incompatibility, missing or contradictory context, incomplete extraction, source hashes and evaluation-file isolation. The rules have not been evaluated on a blind dataset or validated by legal reviewers; no matching accuracy or applicability claim follows.


## Entry 015 — Demonstrate accumulated experience without fabricating authority

**Observation:** Five real synthetic historical source examples could not visually convey what a few hundred prior decisions might mean to a reviewer. Filling the append-only human ledger with invented records would falsely suggest those decisions were taken on inspected documents.

**Decision:** Add a separate, conspicuously fictional 300-entry decision-log explorer with red-flag, amended/resolved, standard/acceptable and context-dependent analogues. Each invented entry links by topic to an existing incoming review, and some link to one of five fixed historical DOCX examples. The relationship is labelled illustrative, not evidential. Nothing enters precedent retrieval, changes routes, or impersonates signed-off legal guidance.

**Evidence and limit:** Deterministic fixture counts, identifiers, source/public JSON parity and link targets are covered by test assertions. This demonstrates information architecture and browsing volume, not source-backed history or actual legal-team learning. A real governed corpus needs reviewed original sources, identity, conditions and explicit publication. Human creative acceptance remains open.
## Issue #5 audit — keyboard access to document intake

**Observation:** In the rendered local queue, Add DOCX looked like a button but the accessibility tree exposed it as plain text because the visible label wrapped a hidden file input. Keyboard navigation could not focus the picker.

**Decision:** Give the control native button semantics and keep the existing hidden file input and upload path. This is a narrow access fix; no route, evidence, or decision behavior changes.

**Evidence and uncertainty:** The before/after accessibility-tree role changed from text to button, and a regression test verifies the markup and click wiring. The file chooser itself, screen-reader output, and mobile layout were not exercised. Owner creative acceptance remains pending.

**Additional queue observation:** The fixed-width queue card forced the contract title into character-by-character wrapping beside its route badge. The title now gets a minimum readable width and may wrap the badge to its own line. A focused CSS regression assertion covers this layout rule; narrow device rendering still needs a real viewport check.

## Issue #5 — The decision action is useful but hard to find

**Observation:** In the owner’s 13 October Home → Falcon walkthrough, the initial review felt busy and the owner could not immediately identify how to act; locating **Record your decision** took effort. The owner described the content as useful but too much was presented at once.

**Decision:** Treat next-action discovery as an unresolved P0 audit finding. Keep full evidence and checks available, and let the owner judge a focused hierarchy proposal before treating the experience as accepted. Do not infer acceptance from the audit or implement a wholesale redesign.

**Evidence and uncertainty:** Owner walkthrough notes are recorded in Issue #5. The local browser run verified desktop keyboard access and the explicit separation between observed wording, suggested route and human decision. A narrow viewport, screen-reader behavior and the full upload/error path remain unverified.

## Issue #5 implementation — put the action on the first screen

**Observation:** Falcon's decision control existed, but at 1280 × 720 the source excerpts pushed it below the fold. The reviewer had to scan evidence before the next action became visible.

**Decision:** Keep the four questions in order. Keep the main finding, explanation and uncertainty visible; put original/reference wording in a native disclosure and place the existing decision action immediately after the concise summary. Secondary findings, provenance, technical checks and history remain reachable through labelled disclosures or the existing evidence tabs.

**Evidence and uncertainty:** The 1280 × 720 screenshot shows the action without scrolling; keyboard activation opened the existing decision form, and an Escalate decision with rationale persisted in an isolated temporary ledger. The available browser surface did not expose a viewport override, so narrow-screen layout is covered by responsive CSS and regression assertions but remains unverified in a resized browser. Creative acceptance remains with the owner.

## Issue #6 — A reference upload is not a baseline change for every family

**Observation:** The existing upload path selected every accepted document as the baseline for new NDA reviews. That behavior cannot safely represent customer-order standards, which use different applicability and comparison components.

**Decision:** Keep one persistent reference library and one source-integrity model. Extract family and applicability from the uploaded source, preserve unknown facts, and register customer orders without changing the selected NDA. Preserve the existing NDA selection behavior while visibly marking uploaded standards as unapproved.

**Evidence and uncertainty:** A distinct synthetic customer-order DOCX and an NDA both persist with their bytes and metadata across an `App` restart; the customer-order upload leaves the NDA selection and prior review binding unchanged. The existing customer-order comparator is not yet connected to incoming order reviews, and no human usability acceptance has been recorded.

## Issue #7 — Match against active standards without turning a suggestion into a decision

**Observation:** The shared context matcher already excluded incompatible scope and abstained on ambiguity, but application matching only saw the fixed research catalogue. PR #11's upload state also used a pre-governance `registered_for_evaluation`/`unapproved` pair that conflicts with the agreed fictional Legal upload flow.

**Decision:** Keep source extraction and the existing reference matcher. Uploaded standards enter as Active and can move to Superseded or Withdrawn with a reason and retained status history. Active standards are eligible for new matches; the bundled NDA remains the legacy baseline for existing review bindings and is excluded from new proposals until its scope is confirmed. Research fixtures remain visible but excluded from app proposals. Superseded and Withdrawn records remain visible and are excluded. A match intake stores the exact original and a hashed proposal snapshot with candidate identity, evidence, exclusions, questions and an empty binding; it does not enter the comparison queue or create a human decision. Existing PR #11 metadata is integrity-checked and migrated to Active on restart without changing original bytes.

**Evidence and uncertainty:** Automated tests cover family/scope proposal, status exclusion and persistence, pre-governance metadata migration, match snapshots across restart, source identity, original-file retrieval, and the unchanged NDA selection. Matching remains deterministic and limited to the current synthetic applicability vocabulary. The local prototype has no authenticated Legal identity, so upload and status actions are self-attested; this records the fictional workflow only. Browser usability and creative acceptance remain with the owner, and no matching accuracy claim follows from the synthetic tests.

## Issue #7 review correction — make reference scope and status legible

**Observation:** Review of PR #13 found that the static demo called eight reference specimens a separate “research library”, buried the actual family-aware library in the local prototype, and described uploaded references as awaiting approval. The bundled NDA's title and extracted context also disagree on mutual versus one-way scope, so it is not safe to use as a newly matched standard.

**Decision:** Present reference standards as one family-aware library, with provenance, version and status visible. Keep the bundled NDA labelled as the legacy baseline for existing review bindings, exclude it from new applicability matching until its scope is confirmed, and keep the eight research specimens visibly grouped as non-Active candidates. Local fictional Legal uploads enter Active; this does not confer legal authority or remove human confirmation. Keep the public experience a static, read-only snapshot and keep incoming examples outside the standards library.

**Evidence and uncertainty:** Python matching tests prove a compatible Active NDA is proposed while a customer-order standard and the legacy baseline are excluded; no comparison runs and human confirmation remains required. Local UI regression tests cover both library grouping and public/local control differences. Creative acceptance and live public-host behavior remain for the owner; no hosting changes were made.

## Issue #15 — Public exploration needs a real review surface

**Observation:** The public static notice was inserted inside the two-column application grid, where it displaced the queue and workspace. The URL form `#/review/T03/overview` was parsed as an unknown route, and the public queue depended on a narrow permanent sidebar. Review data already contained complete extracted incoming/reference wording and precomputed findings, but no dedicated full-comparison view exposed it together.

**Decision:** Keep the public site static and read-only, move its notice below the header, give the queue and selected review the available width, and let every synthetic review open from a native button. Normalize an optional leading slash in hash routes. Show complete incoming and applicable-reference wording side by side and link finding passages to the exported finding details; do not imply that unflagged wording is equivalent.

**Evidence and uncertainty:** Automated coverage now includes slash-prefixed deep links, every queue card, all six exported review comparisons and transient-only public filters. A local Chrome walkthrough opened the direct T03 URL, opened a queue card by keyboard, inspected the paired wording and finding evidence, and exercised browser back. Deployed-host behavior, mobile rendering and human creative acceptance remain unverified before the change is ready for review.

## Issue #19 — Make findings and review language easier to scan

**Observation:** T05 has four findings, but the overview treated one as primary and hid the rest under an “other findings” disclosure. Its two conflict findings came from different paragraphs in the same schedule. The public decision panel also presented save language next to a read-only warning.

**Decision:** Give every finding an equally visible numbered link from the overview, label its source section and paragraph, and keep the total beside the review tabs. Use “No matching clause found” only for an explicitly added-section finding; other missing pairings say that Chug could not confirm a clear match. Replace the named technical headings with reviewer language and explain that public decisions happen in the private workflow and cannot be recorded in the demo. Keep detailed coverage, hashes, source passages and correction tools available.

**Evidence and uncertainty:** Targeted UI tests cover the four T05 findings, distinct paragraph context, navigation anchors, the persistent count, and absent versus unclear reference matches. Browser screenshots and mobile rendering still require human review; no analysis rules or findings changed. Creative acceptance remains with the owner.

## Issue #19 review correction — preserve finding identity and source meaning

**Observation:** Multiple findings can cite the same extracted source passage. Navigating by passage alone reopened the first finding, and XML paragraph indexes were labelled as contract paragraph numbers even when the contract had none.

**Decision:** Carry the selected finding index in the comparison route, open that finding directly, and give every finding associated with a passage its own comparison link. Describe XML anchors as source passages; show the schedule heading with a short wording excerpt in the overview.

**Evidence and uncertainty:** The UI regression suite checks the T05 second and fourth findings through the comparison round trip, verifies all findings attached to shared passages are exposed, and confirms the overview no longer calls XML positions contractual paragraphs. Browser screenshots and mobile rendering still need review; human creative acceptance remains pending.
