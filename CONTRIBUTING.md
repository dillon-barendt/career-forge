# Contributing to CareerForge

Career Forge is currently personal-workflow software with an OSS-ready structure.
Contributions should preserve the existing architecture: domain logic stays
provider-independent, Notion remains the source of truth, and external effects
must be observable and idempotent.

## Local Setup

```bash
uv sync --extra dev
cp .env.example .env
uv run pre-commit install
```

## Development Checks

```bash
scripts/dev_check.sh
```

This runs lint, format, scoped type checking, pytest with an 80% core-coverage
floor, the JSON smoke demo, and the 20-prompt benchmark. If Docker is available,
also run:

```bash
docker build -t career-forge-demo .
docker run --rm career-forge-demo ./demo.sh --json
```

## Pull Request Expectations

- Keep diffs focused.
- Add or update tests for behavior changes.
- Update docs when behavior, configuration, or architecture changes.
- Do not commit real credentials, emails, resumes, or job-search data.
- Prefer provider interfaces over direct API coupling.
- Keep deterministic fixtures fake, stable, and free of personal career data.
- Include machine-readable expectations for benchmark changes.

## Architecture Rules

- Business logic must not depend on Gmail, Notion, or ATS APIs directly.
- Pydantic AI is the intelligence layer.
- Logfire is the observability layer.
- Event logs are append-only.
- Live writes must support dry-run and dedupe behavior.
