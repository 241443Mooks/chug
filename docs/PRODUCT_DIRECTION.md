# Product direction

I want to reduce the repeated work involved in comparing contracts and finding out what was decided last time.

The first job is straightforward: a contract arrives, the system finds the most suitable standard in the library, compares the two, and shows the differences. If it cannot establish a suitable reference, it should say so and keep the document available for review.

The current prototype does this for selected fictional NDAs and customer orders. Matching still misses valid examples. The [README](../README.md) describes the current scope and limits.

## Next steps

- Improve reference matching using separately checked examples. Record wrong matches and unnecessary refusals as well as successes.
- Connect batch or feed intake to a reliable private service. The local batch endpoint and directory script are starting points, not a deployed service.
- Test the review process with people who understand the work. Check whether the findings, evidence and actions help them make decisions.
- Measure whether finding earlier decisions reduces effort without adding administration or encouraging people to apply old outcomes uncritically.

Beyond contracts, I am interested in connecting useful records, decisions and context across existing systems. That has not been built. I would keep source information where it belongs and preserve references to it, rather than copy everything into another system.

## How I want to work

Spend time with the team to understand the work and what already exists. Agree one useful improvement. Take time to build it, bring it back for testing, then revise it from the feedback.

The team knows the routine work, the exceptions and the reasons behind earlier decisions. That knowledge should shape the tool. I do not want to prescribe a large platform before understanding the need.

Use ordinary software where it is sufficient. Test AI against that baseline where there is a specific reason to expect it to help. Neither saved time nor better decisions should be claimed before they have been measured.

The system can organise evidence and suggest connections. People remain responsible for deciding what applies, what risk to accept and what becomes guidance. It should not become a way to increase workloads or monitor people unnecessarily.
