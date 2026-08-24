# Pydantic AI

Pydantic AI is the intelligence layer.

## Current Uses

- email classification
- opportunity evaluation
- fit-score reasoning
- summary generation
- suggested next actions
- interview preparation topics
- resume and cover-letter recommendations

## Service Boundary

`career_ops.ai.factory.build_ai_service()` is the single runtime construction
boundary for Gmail and job-ingestion pipelines:

- `CAREER_FORGE_MODE=mock` is the default and returns `MockAIService` without
  initializing a model provider or reading credentials.
- `CAREER_FORGE_MODE=real` validates credentials and returns
  `PydanticAIService` with implicit deterministic fallback disabled.

`career_ops.ai.pydantic_ai_service.PydanticAIService` owns model calls and
structured outputs. Callers receive Pydantic models, not raw LLM text. Missing
real-mode credentials fail before model construction.

`career_ops.ai.deterministic.DeterministicAIService` implements the same
application-facing protocols behind the mock service for tests, demo, and
benchmarks. Deterministic rules have one owner and mock mode never initializes
a model provider.

## Prompt-Codec Boundary

`career_ops.ai.prompts` owns prompt serialization and output validation:

- `build_email_classifier_prompt()` and `build_opportunity_evaluator_prompt()`
  encode typed inputs as versioned JSON;
- `parse_email_classifier_output()` and `parse_opportunity_evaluator_output()`
  validate provider output into Pydantic domain models.

The service factory does not own prompt text, and application agents do not
own provider parsing. This keeps runtime selection, prompt codecs, and business
workflows independently testable.

## Runtime Modes

Credential-free mock execution works on Python 3.10–3.12:

```bash
CAREER_FORGE_MODE=mock ./demo.sh --json
CAREER_FORGE_MODE=mock uv run python benchmark/bench.py
```

Real execution is explicit:

```bash
export CAREER_FORGE_MODE=real
export CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
export CAREER_FORGE_OPENAI_API_KEY='replace-with-a-secret'
uv run career-forge setup validate
```

## Model Provider Abstraction

The model is configured through `CAREER_FORGE_PYDANTIC_AI_MODEL`, for example:

```bash
CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

Use Pydantic AI with the OpenAI provider directly:

```bash
CAREER_FORGE_OPENAI_API_KEY='replace-with-a-secret'
```

Pydantic AI Gateway routing stays behind the same service boundary:

```bash
CAREER_FORGE_PYDANTIC_AI_GATEWAY_ENABLED=true
CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY='replace-with-a-secret'
CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

The service maps that model to `gateway/openai:gpt-5.2`. If a Gateway routing
group exists, set `CAREER_FORGE_PYDANTIC_AI_GATEWAY_ROUTE` to its slug.

Store live credentials in environment variables or encrypted GitHub Actions
secrets. GitHub Actions sets `CAREER_FORGE_MODE=mock` for its Python 3.10–3.12
test matrix and Python 3.12 quality job; default CI and pull requests never
receive real-provider credentials. Any future live-provider job must be
separately guarded from default CI execution.

## Observability

Each classifier/evaluator call emits:

- agent name
- prompt version
- model string
- gateway enabled flag
- confidence metric
- deterministic fallback metric when used

Prompt eval fixtures can be run with:

```bash
CAREER_FORGE_MODE=mock career-forge evals
```
