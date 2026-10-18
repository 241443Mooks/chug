# Decision 001 — Optional semantic comparison

## Problem and baseline
A lexical and structural comparison reliably surfaces changed wording, omissions and additions. It cannot responsibly decide whether a paraphrase preserves meaning or explain a contextual effect. In the synthetic pack, the clause 3 paraphrase is correctly routed to a person, but the deterministic output can only say that wording differs. A reviewer still needs to interpret it.

## Options
1. Lexical comparison only: zero API cost, transparent, sufficient for routing but no semantic assistance.
2. Local model: avoids third-party transmission but adds install, model-size and operational burden that is disproportionate to this prototype.
3. Narrow opt-in provider comparison of a selected changed clause against the reference: possible help explaining semantic effect, with latency, cost, privacy and hallucination risk.

## Selection and limits
Use option 3 as an **optional aid**, with option 1 as the always-available baseline. The provider receives only selected synthetic source and reference passages. It returns structured explanation, possible effect, uncertainty and existing source anchors. Server validation rejects malformed or invented anchors. It cannot change the deterministic route or make a decision. The reviewer sees provider/model/timestamp and the live status. No call occurs without `CHUG_AI_ENABLED=1`, a local key, positive per-document and session caps, and an explicit UI action and confirmation. The default has no outbound call.

## Business case and verification
The expected advantage is less reviewer effort interpreting language changes like the clause 3 paraphrase. This is a hypothesis, not a measured improvement. The conventional baseline already detects and routes the change. Fixed operating cost is low because this uses Python's standard library and no background service; variable cost and latency depend on the chosen model and output cap. Privacy exposure is bounded to selected synthetic passages. Mocked adapter tests prove failure and anchor handling; they do **not** prove live model quality. A live provider run, observed outputs, pricing, and a reviewer study remain unverified and require explicit authorisation for paid calls. If the provider fails or is absent, the document remains in human review.

## Specification interpretation
“Missing required AI blocks routine” applies when semantic AI is made a required check for a shortcut. This prototype never uses AI as a required shortcut control: a textually changed clause is already `review_required`, and a routine candidate has no substantive change requiring semantic interpretation. The independent full-document controls remain mandatory before a routine candidate appears. This resolves the tension between an optional AI capability and the dataset's template-match routine candidate without a second route or simulated AI.
