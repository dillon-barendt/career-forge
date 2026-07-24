# Providers

Providers isolate external systems from business logic.

## Provider Status

| Provider | Module | Status |
| --- | --- | --- |
| Gmail | `career_ops.gmail` | In progress: OAuth client and dry-run sync service |
| Notion | `career_ops.providers.notion` | In progress: mutation planner, executor, HTTP gateway |
| GitHub | webhook source | In progress: accepted through webhook intake for future Linear automation |
| Linear | planned provider | Planned: execution task sync from GitHub and Career Forge events |
| Greenhouse | `career_ops.providers.jobs` | Scaffolded: provider matching and generic HTML extraction |
| Lever | `career_ops.providers.jobs` | Scaffolded: provider matching and generic HTML extraction |
| Ashby | `career_ops.providers.jobs` | Scaffolded: provider matching and generic HTML extraction |
| Workday | `career_ops.providers.jobs` | Scaffolded: provider matching and metadata fallback |
| LinkedIn | `career_ops.providers.jobs` | Planned/scaffolded: job discovery and relationship tracking |
| Indeed | `career_ops.providers.jobs` | Planned/scaffolded: job discovery provider |

## Job Provider Interface

```python
class JobProvider(Protocol):
    name: str
    def can_handle(self, url: str) -> bool: ...
    def extract(self, url: str, html: str) -> JobPosting: ...
```

Provider output is `JobPosting`. Providers must not write to Notion directly.

## Adding a Provider

1. Add a provider class under `career_ops/providers/jobs/`.
2. Return a normalized `JobPosting`.
3. Register it in `default_job_provider_registry`.
4. Add tests with fake HTML.
5. Document limitations here.

Do not treat a provider as production-supported until it has fixture coverage,
realistic extraction behavior, and live dry-run evidence.

## Workspace Ownership

Use the smallest tool that owns the work:

- GitHub owns repository events, pull requests, checks, and review details.
- Linear owns execution state and should become the automated task system for
  GitHub-driven work.
- Notion owns durable career knowledge and should not mirror noisy execution
  details that are better handled in Linear or GitHub.
