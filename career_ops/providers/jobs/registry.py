from career_ops.providers.jobs.base import JobProvider
from career_ops.providers.jobs.generic import (
    AshbyJobProvider,
    GreenhouseJobProvider,
    IndeedJobProvider,
    LeverJobProvider,
    LinkedInJobProvider,
    WorkdayJobProvider,
)


class JobProviderRegistry:
    def __init__(self, providers: list[JobProvider]) -> None:
        self._providers = providers

    @property
    def providers(self) -> list[JobProvider]:
        return self._providers.copy()

    def find(self, url: str) -> JobProvider | None:
        for provider in self._providers:
            if provider.can_handle(url):
                return provider
        return None


def default_job_provider_registry() -> JobProviderRegistry:
    return JobProviderRegistry(
        providers=[
            LeverJobProvider(),
            GreenhouseJobProvider(),
            AshbyJobProvider(),
            WorkdayJobProvider(),
            LinkedInJobProvider(),
            IndeedJobProvider(),
        ]
    )
