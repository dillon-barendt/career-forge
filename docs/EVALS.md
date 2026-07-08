# Evals

Eval datasets live under `evals/`.

## Current Datasets

- `evals/email_classifier_cases.json`
- `evals/opportunity_evaluator_cases.json`
- `evals/feedback_loop/outcome_cases.json`

## Purpose

Evals make prompt behavior measurable. Each case includes:

- prompt version
- named input
- expected classification or score bounds
- human-review expectation where relevant

## Next Step

Wrap the JSON files in `pydantic_evals.Dataset` and publish evaluation summaries
to Logfire.

Feedback-loop cases should be generated from human overrides, failed
classifications, scoring drift, and application outcomes. Add the case before
loosening automation thresholds.
