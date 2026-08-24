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

The report has exactly these top-level fields: `n`, `median_ms`, `p95_ms`,
`throughput_per_min`, `success_rate`, and `details`. Each `details` item has
exactly `prompt_id`, `latency_ms`, `success`, and `error`.

Fresh 0.6.0 deterministic measurements are:

| Field | Value |
| --- | ---: |
| `n` | 20 |
| `median_ms` | 0.0144865 |
| `p95_ms` | 0.048673 |
| `throughput_per_min` | 2,626,056.166964651 |
| `success_rate` | 1.0 |

CI runs the benchmark in explicit `CAREER_FORGE_MODE=mock` after the Python
3.10–3.12 test matrix passes, then uploads a fresh `benchmark-results.json`
artifact for every push and pull request. No provider credential is available
to this default CI path.

This wraps the JSON files in `pydantic_evals.Dataset`, runs deterministic local
classifier/evaluator behavior against the fixtures, emits Logfire eval traces,
records summary metrics, and appends `prompt_eval.completed` events locally.

Feedback-loop cases should be generated from human overrides, failed
classifications, scoring drift, and application outcomes. Add the case before
loosening automation thresholds.
