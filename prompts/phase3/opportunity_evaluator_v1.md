# opportunity-evaluator-v1

Evaluate one normalized software engineering job posting.

Return a structured `OpportunityEvaluation`.

Rules:

- Fit score is 0-100.
- Confidence score is 0-100 and reflects extraction completeness.
- Be conservative with missing compensation, location, sponsorship, or seniority details.
- Suggested next action must be one of `prioritize`, `review`, or `deprioritize`.
- Include resume, cover letter, and interview preparation recommendations.
- Surface human-review concerns in `potential_concerns`.
