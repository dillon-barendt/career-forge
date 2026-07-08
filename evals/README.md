# Career Forge Evals

These JSON files are lightweight eval datasets for Pydantic Evals or Logfire
dataset import.

Current datasets:

- `email_classifier_cases.json`
- `opportunity_evaluator_cases.json`
- `email_classification/cases.json`
- `opportunity_scoring/cases.json`
- `resume_tailoring/cases.json`
- `followup_generation/cases.json`
- `feedback_loop/outcome_cases.json`

Each dataset includes:

- prompt version
- named cases
- inputs
- expected structured outputs or score bounds

The application does not run these automatically yet. The next step is to wrap
them with `pydantic_evals.Dataset` and publish run summaries to Logfire.

Feedback-loop cases are seeded by real outcomes: overrides, responses,
interviews, offers, rejections, and source-conversion failures.
