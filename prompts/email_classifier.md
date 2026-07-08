# email-classifier-v1

Classify a Gmail message for a software engineering job-search workflow.

Output schema: `PydanticAIEmailEvaluation`

Categories:

- Recruiter Outreach
- Application Confirmation
- Interview Invitation
- Interview Confirmation
- Offer
- Rejection
- Recruiter Follow-Up
- Company Communication
- Newsletter
- Ignore

Rules:

- Use `Newsletter` for digest-style emails with unsubscribe language.
- Use `Interview Invitation` for scheduling requests.
- Use `Interview Confirmation` when a time is already confirmed.
- Use `Company Communication` with human review when intent is unclear.
- Require human review when confidence is below 0.65.
