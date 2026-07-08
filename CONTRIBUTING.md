# Contributing

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
uv run ruff check .
uv run pytest
```

## Pull Request Expectations

- Keep diffs focused.
- Add or update tests for behavior changes.
- Update docs when behavior, configuration, or architecture changes.
- Do not commit real credentials, emails, resumes, or job-search data.
- Prefer provider interfaces over direct API coupling.

## Architecture Rules

- Business logic must not depend on Gmail, Notion, or ATS APIs directly.
- Pydantic AI is the intelligence layer.
- Logfire is the observability layer.
- Event logs are append-only.
- Live writes must support dry-run and dedupe behavior.
