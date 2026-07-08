# Logfire

Logfire is the observability layer for Career Forge.

## Configuration

Development:

```bash
logfire --base-url='https://logfire-us.pydantic.dev' auth
logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'dillon-barendt' 'career-forge'
```

Production-style token:

```bash
export CAREER_FORGE_LOGFIRE_TOKEN=<write-token>
export CAREER_FORGE_LOGFIRE_ENVIRONMENT=local
export CAREER_FORGE_LOGFIRE_BASE_URL=https://logfire-us.pydantic.dev
```

`LOGFIRE_TOKEN` is supported as a compatibility fallback by the runtime, but
`CAREER_FORGE_LOGFIRE_TOKEN` is preferred for this project.

Target project: `dillon-barendt/career-forge`

Target MCP server, if configured outside this repo:
`https://logfire-us.pydantic.dev/mcp`

## Instrumented Boundaries

- Gmail polling
- Gmail message processing
- FastAPI webhook requests
- outbound HTTPX calls
- OpenAI/Pydantic AI model calls
- Pydantic AI email classification
- Pydantic AI opportunity evaluation
- Notion mutation planning/execution
- retry/error events
- feedback-loop metrics and alerts
- webhook receipt, verification, dedupe, handler, and failure events
- prompt eval runs from `career-forge evals`

`Observability.configure()` calls `logfire.configure()` and
`logfire.instrument_pydantic_ai()` when Logfire is installed and configured.
It passes `service_name="career-forge"` and
`advanced=logfire.AdvancedOptions(base_url="https://logfire-us.pydantic.dev")`.
Pydantic AI content capture is disabled by default to avoid sending email or job
posting text as trace content.

## Metrics And Variables

Career Forge registers these Logfire metrics when
`CAREER_FORGE_LOGFIRE_METRICS_ENABLED=true`:

| Metric | Type | Purpose |
| --- | --- | --- |
| `career_forge.ai.requests` | counter | AI classifier/evaluator calls by agent and prompt version |
| `career_forge.ai.fallbacks` | counter | deterministic fallback usage |
| `career_forge.ai.confidence` | histogram | AI confidence scores |
| `career_forge.webhooks.received` | counter | webhook receipts by project/source |
| `career_forge.webhooks.duration_ms` | histogram | webhook ingestion latency |
| `career_forge.evals.cases` | counter | eval cases executed |
| `career_forge.evals.pass_rate` | histogram | eval dataset pass rates |
| `career_forge.catalog.items` | counter | cataloged agents, prompts, LLMs, and providers emitted to Logfire |

Managed variables are enabled with
`CAREER_FORGE_LOGFIRE_VARIABLES_ENABLED=true`. The current code defines:

- `career_forge.ai.gateway_enabled`
- `career_forge.ai.local_fallback_enabled`
- `career_forge.webhooks.enabled`

These variables let Logfire control runtime behavior without redeploying once
remote variables are configured in the Logfire UI.

## AI Gateway

Direct OpenAI remains the default. To route Pydantic AI calls through Pydantic
AI Gateway:

```bash
export CAREER_FORGE_PYDANTIC_AI_GATEWAY_ENABLED=true
export PYDANTIC_AI_GATEWAY_API_KEY=<gateway-key>
export CAREER_FORGE_PYDANTIC_AI_MODEL=openai:gpt-5.2
```

Career Forge converts `openai:gpt-5.2` to the Gateway model string
`gateway/openai:gpt-5.2`. If a Logfire Gateway routing group exists, set:

```bash
export CAREER_FORGE_PYDANTIC_AI_GATEWAY_ROUTE=<routing-group-slug>
```

The service then uses `gateway_provider(..., route=...)` for route-specific
failover/load-balancing.

## Verification

Run a representative dry job:

```bash
CAREER_FORGE_LOGFIRE_TOKEN=<write-token> career-forge evaluate "Logfire smoke test"
```

In Logfire Live view for `dillon-barendt/career-forge`, search for service
`career-forge` and spans named:

- `career_ops.ai.opportunity_evaluation`
- `career_ops.ai.email_classification`
- `career_ops.gmail_poll`
- `career_ops.notion_mutation`

## Event Log vs Logfire

- Event log: durable local replay/debug record.
- Logfire: hosted traces, spans, model-call observability, and trend analysis.

## Feedback Loop

Run:

```bash
career-forge feedback --emit-logfire
```

This emits structured Logfire observations for:

- `career_ops.feedback.metric`
- `career_ops.feedback.alert`

Use those observations to alert on low-confidence spikes, prompt regressions,
source conversion problems, Gmail/Notion failures, and scoring drift. See
[Feedback Loop](FEEDBACK_LOOP.md) for alert thresholds and the improvement
policy.

## Prompt Evals

Run local deterministic prompt evals and publish summaries to Logfire:

```bash
career-forge evals
```

This wraps the JSON fixtures under `evals/` with `pydantic_evals.Dataset`,
emits Pydantic Evals traces, writes `prompt_eval.completed` events to the local
event log, and records eval metrics in Logfire.

## Agents, Prompts, LLMs, And Providers

Sync the project catalog into Logfire:

```bash
career-forge logfire-sync
```

This emits structured metadata records for:

- agents from `career_ops/agents/`
- prompt templates from `prompts/`
- direct OpenAI, Pydantic AI Gateway, and deterministic fallback LLM paths
- Gmail, Notion, Logfire, webhook, ATS, and Gateway providers

Each record uses `career_ops.catalog.<kind>` with fields for `name`, `version`,
`owner`, `status`, `description`, `path`, and `tags`, plus the
`career_forge.catalog.items` metric.

## Webhook Channels

The current tool environment did not expose a Logfire MCP mutation tool for
creating channels or destination routing, so webhook channel routing is
documented here for manual setup.

Create or update these channels in the Logfire project:

| Channel | Purpose | Alerting |
| --- | --- | --- |
| `career-forge.webhooks.received` | Normal webhook intake, route resolution, verifier status, dedupe generation, and handler completion | Low-noise stream; no page unless volume drops unexpectedly |
| `career-forge.webhooks.failed` | Handler exceptions and failed processing results | Alert on any sustained failures or repeated source failure |
| `career-forge.webhooks.security` | Verification failures, unsupported signatures, suspicious headers, and future replay protection failures | Higher-priority alert |
| `career-forge.webhooks.deadletter` | Accepted events that cannot be processed or mapped to a handler workflow | Review queue or issue destination |
| `career-forge.webhooks.notion` | Notion-specific webhook activity for `career-forge/notion` | Source-specific stream; alert if Notion traffic starts failing |

The webhook code emits structured fields:

```text
project_name
source_name
event_id
dedupe_key
signature_status
processing_status
duration_ms
error_type
```

Do not log full webhook payloads by default. Header metadata is redacted for
authorization, cookie, API key, and provider signature headers. Future sources
should add their own source channel, for example
`career-forge.webhooks.github`, while still emitting failures and verification
problems to the shared failed/security channels.

Triage failures in this order:

1. Check `career-forge.webhooks.security` for verifier or signature problems.
2. Check `career-forge.webhooks.failed` for handler exceptions and `error_type`.
3. Check `career-forge.webhooks.deadletter` for accepted but unmapped events.
4. Use `dedupe_key` and `event_id` to correlate with provider retry behavior.
