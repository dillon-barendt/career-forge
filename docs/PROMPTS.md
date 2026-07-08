# Prompts

Prompt templates live under `prompts/` and are versioned in file names or
headers.

## Current Prompt Versions

| Prompt | Version |
| --- | --- |
| Email classifier | `email-classifier-v1` |
| Opportunity evaluator | `opportunity-evaluator-v1` |
| Resume tailor | legacy prompt |
| Cover letter | legacy prompt |
| Recruiter outreach | legacy prompt |
| Interview prep | legacy prompt |

## Rules

- Prompt versions must be stable once used in production traces.
- New prompt behavior should create a new version.
- Prompts should describe the expected structured output schema.
- Prompt changes should update eval fixtures.
