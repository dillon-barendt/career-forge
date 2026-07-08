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

The model is configured through `CAREER_OPS_PYDANTIC_AI_MODEL`, for example:

```bash
CAREER_OPS_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

For tonight, use Pydantic AI with the OpenAI provider directly:

```bash
OPENAI_API_KEY=sk-...
```

Pydantic AI Gateway routing should remain behind this service boundary and can
be added later when the gateway base URL/token are available.

## Dry-Run Behavior

When provider credentials are missing, the service falls back to deterministic
local evaluation if `allow_local_fallback=True`. This keeps CLI dry-runs and
tests usable without live model calls.
