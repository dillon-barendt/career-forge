from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordRule:
    keyword: str
    points: int
    reason: str


POSITIVE_RULES = [
    KeywordRule("python", 12, "Python is a strong skill match."),
    KeywordRule("fastapi", 10, "FastAPI/API experience is directly relevant."),
    KeywordRule("django", 7, "Django backend experience is relevant."),
    KeywordRule("postgres", 8, "Postgres experience maps well to backend work."),
    KeywordRule("distributed", 7, "Distributed systems experience is a useful match."),
    KeywordRule("observability", 6, "Observability work is a useful differentiator."),
    KeywordRule("ai", 6, "AI product or tooling work is relevant."),
    KeywordRule("remote", 5, "Remote role preference is a positive signal."),
    KeywordRule("senior", 5, "Seniority appears aligned with experienced engineering roles."),
]

NEGATIVE_RULES = [
    KeywordRule("onsite", -10, "Onsite-only roles may reduce fit."),
    KeywordRule("java only", -12, "Java-only roles are less aligned with this pipeline."),
    KeywordRule("clearance", -8, "Clearance requirements may be a blocker."),
    KeywordRule("unpaid", -20, "Unpaid roles should not enter the full-time pipeline."),
]


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())
