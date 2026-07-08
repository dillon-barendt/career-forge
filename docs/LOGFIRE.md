# Logfire

Logfire is the observability layer for Career Forge.

## Configuration

Development:

```bash
logfire --base-url='https://logfire-us.pydantic.dev' auth
logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'dillon-barendt' 'career-forge'
```

Current hosted-project note: creating `dillon-barendt/career-forge` may fail
with `Projects limit reached` until an old Logfire project is removed or the
limit is raised. In that case, keep local Logfire auth pointed at the existing
`dillon-barendt/career-ops` project and use `service_name="career-forge"` so
new traces remain distinguishable.

Production-style token:

```bash
export CAREER_FORGE_LOGFIRE_TOKEN=<write-token>
export CAREER_FORGE_LOGFIRE_ENVIRONMENT=local
export CAREER_FORGE_LOGFIRE_BASE_URL=https://logfire-us.pydantic.dev
```

`LOGFIRE_TOKEN` is supported as a compatibility fallback by the runtime, but
`CAREER_FORGE_LOGFIRE_TOKEN` is preferred for this project.

Target project: `dillon-barendt/career-forge` when available. Temporary local
fallback: `dillon-barendt/career-ops`.

Target MCP server, if configured outside this repo:
`https://logfire-us.pydantic.dev/mcp`

## Instrumented Boundaries

- Gmail polling
- Gmail message processing
- Pydantic AI email classification
- Pydantic AI opportunity evaluation
- Notion mutation planning/execution
- retry/error events
- feedback-loop metrics and alerts
- webhook receipt, verification, dedupe, handler, and failure events

`Observability.configure()` calls `logfire.configure()` and
`logfire.instrument_pydantic_ai()` when Logfire is installed and configured.
It passes `service_name="career-forge"` and
`advanced=logfire.AdvancedOptions(base_url="https://logfire-us.pydantic.dev")`.
Pydantic AI content capture is disabled by default to avoid sending email or job
posting text as trace content.

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
