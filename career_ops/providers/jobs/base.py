from collections.abc import Mapping
from typing import Protocol

import httpx

from career_ops.models import JobPosting


class JobPageFetcher(Protocol):
    def fetch(self, url: str) -> str:
        """Return the HTML for a job posting URL."""


class JobProvider(Protocol):
    name: str

    def can_handle(self, url: str) -> bool:
        """Return true when this provider can extract the URL."""

    def extract(self, url: str, html: str) -> JobPosting:
        """Extract a normalized job posting from provider HTML."""


class HttpxJobPageFetcher:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def fetch(self, url: str) -> str:
        response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text


class StaticJobPageFetcher:
    def __init__(self, pages: Mapping[str, str]) -> None:
        self._pages = dict(pages)

    def fetch(self, url: str) -> str:
        return self._pages[url]
