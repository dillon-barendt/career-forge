from typing import Protocol

from pydantic import BaseModel, Field

from career_ops.models import AgentResult, AuditEvent


class AgentContext(BaseModel):
    run_id: str
    dry_run: bool = True
    audit_events: list[AuditEvent] = Field(default_factory=list)


class CareerAgent(Protocol):
    name: str

    def run(self, context: AgentContext) -> AgentResult:
        """Execute one agent step."""
