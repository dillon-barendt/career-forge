# Providers

Providers isolate external systems from business logic.

## Implemented Provider Families

| Provider | Module | Status |
| --- | --- | --- |
| Gmail | `career_ops.gmail` | OAuth client and sync service |
| Notion | `career_ops.providers.notion` | mutation planner, executor, HTTP gateway |
| Greenhouse | `career_ops.providers.jobs` | HTML extractor |
| Lever | `career_ops.providers.jobs` | HTML extractor |
| Ashby | `career_ops.providers.jobs` | HTML extractor |
| Workday | `career_ops.providers.jobs` | HTML extractor with metadata fallback |
| LinkedIn | `career_ops.providers.jobs` | HTML extractor scaffold |
| Indeed | `career_ops.providers.jobs` | HTML extractor scaffold |

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
