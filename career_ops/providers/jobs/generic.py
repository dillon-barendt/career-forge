import re
from html import unescape
from urllib.parse import urlparse

from career_ops.models import JobPosting

SKILL_KEYWORDS = {
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "postgres": "Postgres",
    "postgresql": "Postgres",
    "observability": "Observability",
    "distributed systems": "Distributed Systems",
    "aws": "AWS",
    "kubernetes": "Kubernetes",
    "typescript": "TypeScript",
    "react": "React",
    "sql": "SQL",
}


class HtmlJobProvider:
    name = "generic"
    host_tokens: tuple[str, ...] = ()

    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(token in host for token in self.host_tokens)

    def extract(self, url: str, html: str) -> JobPosting:
        text = self._html_to_text(html)
        role = self._extract_role(html, text)
        company = self._extract_company(url, html, role)
        location = self._extract_labeled_value(text, "Location")
        compensation = self._extract_labeled_value(text, "Compensation")
        employment_type = self._extract_labeled_value(text, "Employment Type")
        skills = self._extract_skills(text)

        return JobPosting(
            source_url=url,
            provider=self.name,
            company=company,
            role=role,
            location=location,
            compensation=compensation,
            employment_type=employment_type,
            remote_policy=self._remote_policy(text),
            description=text,
            skills=skills,
            tech_stack=[skill for skill in skills if skill in {"Python", "Postgres", "TypeScript"}],
            apply_url=url,
        )

    def _html_to_text(self, html: str) -> str:
        html = re.sub(r"(?i)<br\s*/?>", "\n", html)
        html = re.sub(r"(?i)</(?:p|div|h1|h2|li)>", "\n", html)
        text = re.sub(r"<[^>]+>", " ", html)
        return " ".join(unescape(text).split())

    def _extract_role(self, html: str, text: str) -> str:
        h1 = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
        if h1:
            return self._clean_text(h1.group(1))

        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
        if title:
            return self._clean_text(title.group(1).split(" - ")[0])

        role = re.search(r"\b([A-Z][A-Za-z0-9 /\-]+(?:Engineer|Developer|Lead|Manager))\b", text)
        return role.group(1).strip() if role else "Software Engineering Opportunity"

    def _extract_company(self, url: str, html: str, role: str) -> str:
        metadata_company = self._extract_metadata_company(html)
        if metadata_company:
            return metadata_company

        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
        if title and " - " in title.group(1):
            candidate = title.group(1).split(" - ")[-1]
            return self._clean_text(candidate)

        host_company = self._extract_host_company(url)
        if host_company:
            return host_company

        path_parts = [part for part in urlparse(url).path.split("/") if part]
        if path_parts:
            return path_parts[0].replace("-", " ").title()

        host = urlparse(url).netloc.split(".")[0]
        return host.replace("-", " ").title() or role

    def _extract_metadata_company(self, html: str) -> str | None:
        match = re.search(
            r'(?is)<meta[^>]+(?:property|name)=["\']og:site_name["\'][^>]+content=["\']([^"\']+)',
            html,
        )
        if not match:
            return None
        value = self._clean_text(match.group(1))
        return re.sub(r"\s+Careers?$", "", value, flags=re.IGNORECASE)

    def _extract_host_company(self, url: str) -> str | None:
        host = urlparse(url).netloc.lower()
        if "myworkdayjobs.com" in host:
            first_part = host.split(".", maxsplit=1)[0]
            return first_part.replace("-", " ").title()
        return None

    def _extract_labeled_value(self, text: str, label: str) -> str | None:
        pattern = rf"{re.escape(label)}:\s*(.+?)(?=\s+[A-Z][A-Za-z ]+:\s|$)"
        match = re.search(pattern, text)
        return match.group(1).strip(" .") if match else None

    def _extract_skills(self, text: str) -> list[str]:
        normalized = text.lower()
        return [label for keyword, label in SKILL_KEYWORDS.items() if keyword in normalized]

    def _remote_policy(self, text: str) -> str | None:
        normalized = text.lower()
        if "remote" in normalized:
            return "Remote"
        if "hybrid" in normalized:
            return "Hybrid"
        if "onsite" in normalized or "on-site" in normalized:
            return "Onsite"
        return None

    def _clean_text(self, value: str) -> str:
        return " ".join(re.sub(r"<[^>]+>", " ", unescape(value)).split()).strip()


class LeverJobProvider(HtmlJobProvider):
    name = "lever"
    host_tokens = ("jobs.lever.co",)


class GreenhouseJobProvider(HtmlJobProvider):
    name = "greenhouse"
    host_tokens = ("greenhouse.io", "boards.greenhouse.io")


class AshbyJobProvider(HtmlJobProvider):
    name = "ashby"
    host_tokens = ("ashbyhq.com",)


class WorkdayJobProvider(HtmlJobProvider):
    name = "workday"
    host_tokens = ("myworkdayjobs.com", "workdayjobs.com")


class LinkedInJobProvider(HtmlJobProvider):
    name = "linkedin"
    host_tokens = ("linkedin.com",)


class IndeedJobProvider(HtmlJobProvider):
    name = "indeed"
    host_tokens = ("indeed.com",)
