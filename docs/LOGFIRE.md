# Logfire

Logfire is the observability layer for Career Ops.

## Configuration

Development:

```bash
logfire --base-url='https://logfire-us.pydantic.dev' auth
logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'dillon-barendt' 'career-ops'
```

Production-style token:

```bash
export CAREER_OPS_LOGFIRE_TOKEN=<write-token>
export CAREER_OPS_LOGFIRE_ENVIRONMENT=local
export CAREER_OPS_LOGFIRE_BASE_URL=https://logfire-us.pydantic.dev
```

`LOGFIRE_TOKEN` is supported as a compatibility fallback by the runtime, but
`CAREER_OPS_LOGFIRE_TOKEN` is preferred for this project.

Target project: `dillon-barendt/career-ops`

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

`Observability.configure()` calls `logfire.configure()` and
`logfire.instrument_pydantic_ai()` when Logfire is installed and configured.
It passes `service_name="career-ops"` and
`advanced=logfire.AdvancedOptions(base_url="https://logfire-us.pydantic.dev")`.
Pydantic AI content capture is disabled by default to avoid sending email or job
posting text as trace content.

## Verification

Run a representative dry job:

```bash
CAREER_OPS_LOGFIRE_TOKEN=<write-token> career-ops evaluate "Logfire smoke test"
```

In Logfire Live view for `dillon-barendt/career-ops`, search for service
`career-ops` and spans named:

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
career-ops feedback --emit-logfire
```

This emits structured Logfire observations for:

- `career_ops.feedback.metric`
- `career_ops.feedback.alert`

Use those observations to alert on low-confidence spikes, prompt regressions,
source conversion problems, Gmail/Notion failures, and scoring drift. See
[Feedback Loop](FEEDBACK_LOOP.md) for alert thresholds and the improvement
policy.
