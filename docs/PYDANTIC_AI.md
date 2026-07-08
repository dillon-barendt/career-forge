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

`career_ops.ai.pydantic_ai_service.PydanticAIService` owns model calls and
structured outputs. Callers receive Pydantic models, not raw LLM text.

## Model Provider Abstraction

The model is configured through `CAREER_FORGE_PYDANTIC_AI_MODEL`, for example:

```bash
CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

For tonight, use Pydantic AI with the OpenAI provider directly:

```bash
OPENAI_API_KEY=sk-...
```

Pydantic AI Gateway routing stays behind the same service boundary:

```bash
CAREER_FORGE_PYDANTIC_AI_GATEWAY_ENABLED=true
PYDANTIC_AI_GATEWAY_API_KEY=pylf_...
CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

The service maps that model to `gateway/openai:gpt-5.2`. If a Gateway routing
group exists, set `CAREER_FORGE_PYDANTIC_AI_GATEWAY_ROUTE` to its slug.

## Dry-Run Behavior

When provider credentials are missing, the service falls back to deterministic
local evaluation if `allow_local_fallback=True`. This keeps CLI dry-runs and
tests usable without live model calls.

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
career-forge evals
```
