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

## Run Evals

Run:

```bash
career-forge evals
```

This wraps the JSON files in `pydantic_evals.Dataset`, runs deterministic local
classifier/evaluator behavior against the fixtures, emits Logfire eval traces,
records summary metrics, and appends `prompt_eval.completed` events locally.

Feedback-loop cases should be generated from human overrides, failed
classifications, scoring drift, and application outcomes. Add the case before
loosening automation thresholds.
