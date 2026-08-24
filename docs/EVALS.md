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

The public `benchmark/prompts.json` suite complements prompt evals with 20
credential-free contract cases and latency measurements. Benchmark success is
defined by literal classifications, score floors, and recommended actions.

## Run Evals

Run:

```bash
career-forge evals
```

Run the reproducible benchmark and write its machine-readable report:

```bash
uv run python benchmark/bench.py --output benchmark/results.json
```

CI uploads a fresh benchmark JSON artifact for every push and pull request.

This wraps the JSON files in `pydantic_evals.Dataset`, runs deterministic local
classifier/evaluator behavior against the fixtures, emits Logfire eval traces,
records summary metrics, and appends `prompt_eval.completed` events locally.

Feedback-loop cases should be generated from human overrides, failed
classifications, scoring drift, and application outcomes. Add the case before
loosening automation thresholds.
