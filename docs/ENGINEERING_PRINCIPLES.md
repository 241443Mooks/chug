# Engineering rules

- Use the simplest approach that meets the task. Hashing, extraction, comparison, routing and records do not need AI by default.
- Preserve original files, source identity and evidence links. Make failures visible. Do not recommend routine review when required checks did not complete.
- Keep comparisons, human assessments, contract actions and published guidance separate.
- Test behaviour against source evidence. Keep evaluation answer keys out of runtime inputs. Do not tune a matcher against results described as held out.
- Distinguish synthetic test results, mocked provider responses and live observations. Do not invent accuracy, savings or legal conclusions.
- Before adding AI, state the unmet need, ordinary-software baseline, expected benefit, failure handling, cost and privacy implications. Record significant choices in `docs/decisions/`.
- Keep the local synthetic workflow reproducible without provider credentials. Do not introduce production abstractions before a working use case needs them.

For a substantial change, explain the problem, changed behaviour, checks run and remaining limits. Human usability review, legal validation and production readiness are separate from passing tests.

For documentation and interface copy, follow [the repository writing rules](../AGENTS.md).
