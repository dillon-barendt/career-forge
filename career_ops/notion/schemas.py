from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class ApplicationStatus(StrEnum):
    NEW = "new"
    REVIEWING = "reviewing"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    CLOSED = "closed"


class JobOpportunity(BaseModel):
    title: str
    company: str
    description: str = ""
    url: HttpUrl | None = None
    location: str | None = None
    compensation: str | None = None
    source: str | None = None
    status: ApplicationStatus = ApplicationStatus.NEW
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class Company(BaseModel):
    name: str
    website: HttpUrl | None = None
    industry: str | None = None
    notes: str = ""


class Contact(BaseModel):
    name: str
    company: str | None = None
    role: str | None = None
    linkedin_url: HttpUrl | None = None
    email: str | None = None
    notes: str = ""


class Application(BaseModel):
    opportunity_title: str
    company: str
    status: ApplicationStatus = ApplicationStatus.NEW
    applied_on: date | None = None
    follow_up_on: date | None = None
    next_action: str | None = None


class MaterialDraft(BaseModel):
    opportunity_title: str
    company: str
    kind: str
    body: str


class FitScore(BaseModel):
    score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    recommended_action: str
