# Issue #6 — Upload and persist contract reference standards

## Scope

Implement the first reference-library milestone on the `chug/` application path. Reference originals share the existing `state_dir/references/` persistence area. The verified research catalogue remains the source for bundled research candidates; locally uploaded entries join the same library view and retain their exact source bytes.

Uploads are marked `registered_for_evaluation` and `unapproved`. This feature does not add an approval workflow. An uploaded mutual NDA retains the existing behavior of becoming the selected reference for new NDA uploads; its use is evaluation only and does not imply approval. A customer-order upload is stored separately and does not alter the selected NDA or existing review bindings.

## Recorded metadata

Each uploaded entry records a stable content-derived reference ID, display name (from the original filename), family, extracted applicability facts with unknown or ambiguous values preserved, original filename, SHA-256, version, registration status, approval status, provenance and extraction coverage/limitations. Duplicate source bytes return the existing entry without changing its name, version or status.

The local API exposes a read-only library listing and detail, with an original download that verifies the stored bytes against SHA-256. Upload remains on the private Python backend. The public static demo retains its read-only behavior.

## Verification record

- Base: `8a136ab3b174c02b65f5b225aa81959b052d81ec` (`chug/main`, 2026-10-18).
- Focused reference checks: `python3 -m unittest tests.test_reference_library tests.test_reference_selection -v` — 9 passed.
- Full regression suite: `python3 -m unittest discover -s tests -q` — 63 passed.
- NDA evaluator: `python3 -m tests.evaluate` — 6/6 route agreement (T01–T06).
- Web source and UI regressions: `node --check web/app.js` — passed; `node --test tests/test_web_ui.mjs` — 13 passed.
- `git diff --check` — passed.
- The first sandboxed focused HTTP run could not bind a loopback port; rerunning the focused and full Python suites with loopback permission succeeded. No test depended on a live AI provider.
- Local UI acceptance: opened the Reference page, inspected a customer-order detail and the exact-original link, then uploaded a distinct fictional customer-order DOCX through the same multipart endpoint used by the hidden file picker (the available browser UI automation could not operate the hidden native file input). The UI displayed its family, registration and approval statuses, provenance, SHA-256, verified source and complete extraction.
- Restart and byte-integrity acceptance: stopped and restarted the local Python server with the same isolated state directory. The uploaded reference ID, metadata and verified detail returned after restart; its downloaded original SHA-256 matched the uploaded DOCX (`33bee2706fb7483ae7954a767300113774cb3301bb06495b1ae2682acd8848c9`). The current NDA reference remained `2c9ab77e5256c2cd1a964955d97ab8f002fee40c26c61c2f23bae56da707e817` before and after.
- Browser interaction coverage: detail and post-restart visibility were checked in the local UI. The native file chooser itself was not driven through the browser; the endpoint upload and resulting UI state were verified instead. UI regression tests also passed, including the public static upload-hidden state.
- Human creative acceptance: pending; this implementation does not self-certify the review experience.

## Limitations and decisions

- Family identification and applicability fields use the existing deterministic extraction context. Unknown facts remain unknown; this is not a legal validation of the uploaded wording.
- New customer-order standards are stored and viewable but are not yet bound to incoming order reviews or the review queue. The existing customer-order comparison component remains a separate explicit-confirmation path.
- Uploaded reference version defaults to `1.0`; the filename stem supplies the display name. No approval controls are introduced in this issue.
- PR #3 is intentionally left untouched. Reconcile its hosting changes after PR #11 is accepted, as requested; this branch makes no changes to PR #3.
