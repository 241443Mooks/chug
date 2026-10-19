# Chug

A contract comparison prototype built for the PortSwigger application exercise. It uses fictional documents.

The immediate job is “spot the difference”: find a suitable reference, compare the incoming contract with it, and show the wording that needs a person's attention.

## What works now

- The local app accepts DOCX files, individually or in batches of up to 20.
- It searches the active reference library and compares supported NDAs and customer orders when it finds a suitable match. If it cannot select a reference, it keeps the file in the queue and explains why comparison did not run.
- Reviewers can inspect source wording and original files, assess findings, and accept a contract or flag it for further review. Other recorded outcomes include requesting amendments, rejection and escalation.
- It keeps decisions and their evidence. A reviewer can explicitly share a decision for later retrieval or withdraw it.
- The [public demo](https://chug.smooks.co.uk) shows fictional reviews. It cannot accept uploads or save decisions. Changes in this repo do not establish what is currently deployed.

The comparison works without AI. An optional AI clause explanation is off by default; its usefulness has not been established.

## What does not work yet

Matching is limited. In the recorded ten-file blinded fixture check, it chose five correct references, left three matchable files unmatched, and correctly declined both unsupported examples. This is a small synthetic check, not a general accuracy result. See the [test record](docs/INTEGRATED_REVIEW_ACCEPTANCE.md).

This version does not support PDFs or scanned documents. It has no connected document feed, built-in scheduler, production access controls or cross-system knowledge map. It does not provide legal advice and has not been validated for real legal work. Use fictional files only.

## What it is being built to do

Process incoming contracts without someone classifying each one by hand, show differences against an appropriate standard, and make relevant earlier decisions easier to find. A local directory import script exists; a live feed and reliable private hosting still need work.

The wider question is whether recording the evidence and reasoning from one review can reduce repeated work in the next. That benefit is not yet measured.

## What it must never decide

It must never approve a contract, accept legal risk or turn a past decision into policy on someone's behalf. It cannot guarantee that it has found every issue or that an agreement is safe to sign. Those are limits of the role, not missing features.

[Run it and try the examples](START_HERE.md) · [Product direction](docs/PRODUCT_DIRECTION.md) · [Technical scope](docs/PRODUCT_SPEC.md)

[Proprietary licence: evaluation only](LICENSE.md). Reuse, redistribution and commercial use require written permission.
