# Try Chug

Chug compares fictional contracts with reference documents. Start with the [README](README.md) for what it can and cannot do.

## Public demo

Open [chug.smooks.co.uk](https://chug.smooks.co.uk), then the review queue. Try Falcon Data for a flagged clause, Brookside AI for a past decision, and Birchbridge for a routine candidate. Inspect the findings, comparison and original documents.

The public demo is read-only. The review choices are examples; they do not save anything. It may differ from the latest local version.

## Run locally

Use Python 3.9 or newer. The core DOCX workflow needs no extra Python packages, account or AI credentials. From the repository root:

```sh
python3 scripts/seed_synthetic_starter.py --state-dir ./chug-starter
python3 -m chug.server --port 8771 --state-dir ./chug-starter
```

Open `http://127.0.0.1:8771`. This creates a separate local workspace containing two fictional standards and five incoming files:

| Example | Expected result |
| --- | --- |
| Exact NDA copy | Reference selected; no differences reported |
| NDA with longer retention | Reference selected; differences shown |
| Exact reseller order copy | Reference selected; no differences reported |
| Order with more seats | Reference selected; differences shown |
| Ambiguous reseller cloud purchase | No suitable reference; comparison not run |

All five start without a human decision. No differences does not mean approved.

Open a changed example. Inspect the selected reference, comparison and original files. Confirm that the reference applies. Open a finding and record an assessment: Not relevant, Acceptable, Problem, Needs further review or Deal breaker. Assessments and contract decisions are separate. Try **Flag for further review** and inspect the history. **Accept contract** requires acknowledgement that you independently reviewed the original; unresolved findings require an additional acknowledgement and explanation.

Use fictional files only. The local app has no production authentication or verified reviewer roles. State stays in the directory passed to `--state-dir`; without that option it uses `.chug-data/`.

For new uploads, add a suitable fictional standard through **References**, then use **Upload DOCX contracts**. Selection and comparison run automatically when the source gives enough evidence. See [intake details](docs/EXPLICIT_REFERENCE_UPLOAD.md) for batches and the directory script.

## Try reusing a decision

Use a separate workspace for this exercise:

```sh
python3 -m chug.server --port 8772 --state-dir ./chug-learning
```

Open `http://127.0.0.1:8772`.

1. Upload `dataset/learning/L01-audit-retention.docx`. Inspect the wording and record a fictional decision with its conditions.
2. Open its review history and choose **Share this decision as a precedent**. Recording and sharing are separate actions.
3. Upload `dataset/learning/L02-analytics-retention.docx`. Inspect the retrieved decision. Regulatory retention and commercial analytics are different purposes; the earlier outcome does not settle this case.
4. Withdraw the shared decision from the first review. It should stop appearing as active precedent while its history remains recorded.

Reviewer authority is self-declared in this demo. This exercise shows storage and retrieval, not verified legal reasoning or model training.

## Checks

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
node --check web/app.js
node --test tests/test_web_ui.mjs
python3 -m tests.evaluate
python3 -m tests.adversarial_audit
```

Node.js is needed for the JavaScript checks. These checks test defined examples, not legal completeness. The [integration record](docs/INTEGRATED_REVIEW_ACCEPTANCE.md) contains the pilot, blinded matching results and browser checks, including failures and remaining gaps.

The [optional AI adapter](docs/AI_ARCHITECTURE.md) requires deliberate configuration and an explicit action. It is not needed for these exercises.
