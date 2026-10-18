# Chug public static demonstration

## Why this exists

The deployed static frontend requests /api/queue and /api/reference. When the site is published without the Python server, the host may return index.html to those URLs, causing a JSON parse error. This is a deployment mismatch, not missing NDA fixtures.

**The public static option is read-only and uses synthetic documents only.** It is not the working reviewer/decision backend, a production deployment, or legal approval. Never expose the current Python server to the public Internet unchanged: it has local-demo trust assumptions, no authentication or production data separation, and supports writing review events and uploading files.

## Build the website data

Prerequisites: Python 3.9+ and the complete repository with research PR #20's twenty synthetic client fixtures. From repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node --check web/app.js
node --test tests/test_web_ui.mjs
python3 scripts/export_public_demo.py
```

The exporter writes **web/demo-data/** with:

- Six original NDA cases with actual precomputed analysis, full source evidence and references, matching the current supported engine.
- Five historical records with original synthetic DOCX files.
- A separate, **fictional** 300-entry decision log, accessible at `/decision-log.html`, linked by topic to current reviews and some fixed historical example DOCX files. These entries are not verified precedents or source-backed legal decisions.
- Original baseline NDA, preserving source hashes.
- Eight **unapproved** research reference specimens.
- Twenty routine-looking client specimen files when PR #20 is present. These are **not analysed**, not blind matching tests and not automatically bound to a standard.
- Four research challenge specimens that are **not analysed** and do not expose their expected-match answers.

The export starts with a fresh empty ledger and exports **no reviewer names, uploaded contracts, user choices, model calls, private app state, ground-truth files or evaluation-only answers**.

## Publish

Configure the static host's publish directory as `web/`. Ensure every file under `web/demo-data/` is included in the deployment; merely deploying `web/index.html`, `app.js` and `styles.css` is not sufficient.

When the browser requests `/api/queue` and receives a non-JSON static fallback, Chug will load `/demo-data/queue.json` instead, display the read-only public notice and disable all write controls. Reference and individual review pages load snapshot JSON and link to exported original fictional DOCX files. If the host does not support this static fallback, add an appropriate rewrite to `/index.html` for SPA routes but do not rewrite `/demo-data/*` to HTML.

The experimental branch has a workflow to run validation, produce the snapshot, and commit generated files **to that feature branch** when Actions are enabled. If Actions are disabled, run the commands above before publishing. This does not automatically update the existing public deployment until the relevant PRs are accepted and the website is redeployed.

## Smoke check

1. `https://chug.smooks.co.uk/demo-data/queue.json` returns `application/json` and exactly six `items`.
2. `/demo-data/reference.json` shows the bundled fictional reference.
3. `/demo-data/research.json` lists 8 standards, 20 ordinary-looking client files, and 4 challenge documents, all flagged as research specimens.
4. Home shows nonzero counts; open Falcon and inspect linked source passages. Reference shows the research specimens.
5. Download a synthetic original DOCX from a review and the research library.
6. Confirm the public read-only banner appears and no upload, decision, publication or AI action is offered.
7. Open `/decision-log.html`, filter on Falcon (T03), verify red flags and amended green examples are labelled as fictional, and follow its link back to the current review.
8. Recheck at narrow viewport. Do not claim human creative or legal acceptance before it happens.

## Full interactive service: a separate decision

A live reviewer session requires a **secure Python backend**, rather than static hosting. Before any Internet-accessible backend, define authentication, access boundaries, persistence/backups, CSRF/origin controls, HTTPS, rate limits, upload/content validation, and safeguards for real document handling. Avoid publishing review event APIs with unauthenticated write access. The existing offline server should remain loopback-only until this design is made deliberately.

Multi-family applicability suggestion and customer-order comparison are **not implemented** by this snapshot. Those belong to issue #21. Do not present the research fixtures as validated legal guidance or auto-approved matches.
