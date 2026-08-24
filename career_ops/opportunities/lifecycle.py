from typing import Final

from pydantic import BaseModel, Field, HttpUrl, computed_field
from pydantic_graph import Graph, GraphBuilder
from pydantic_graph.step import StepContext

from career_ops.compat import StrEnum

TransitionMap = dict["OpportunityLifecycleState", tuple["OpportunityLifecycleState", ...]]


class OpportunityLifecycleState(StrEnum):
    SOURCED = "sourced"
    NORMALIZED = "normalized"
    COMPANY_RESEARCHED = "company_researched"
    FIT_SCORED = "fit_scored"
    MATERIALS_READY = "materials_ready"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    CLOSED_REJECTED = "closed_rejected"
    CLOSED_LOW_FIT = "closed_low_fit"
    CLOSED_DUPLICATE = "closed_duplicate"


NEXT_ACTIONS: Final[dict[OpportunityLifecycleState, str]] = {
    OpportunityLifecycleState.SOURCED: "normalize_opportunity",
    OpportunityLifecycleState.NORMALIZED: "research_company",
    OpportunityLifecycleState.COMPANY_RESEARCHED: "score_fit",
    OpportunityLifecycleState.FIT_SCORED: "prepare_materials_or_close_low_fit",
    OpportunityLifecycleState.MATERIALS_READY: "submit_application",
    OpportunityLifecycleState.APPLIED: "schedule_follow_up",
    OpportunityLifecycleState.FOLLOW_UP_DUE: "send_follow_up",
    OpportunityLifecycleState.CLOSED_REJECTED: "none",
    OpportunityLifecycleState.CLOSED_LOW_FIT: "none",
    OpportunityLifecycleState.CLOSED_DUPLICATE: "none",
}

CLOSED_STATES: Final[set[OpportunityLifecycleState]] = {
    OpportunityLifecycleState.CLOSED_REJECTED,
    OpportunityLifecycleState.CLOSED_LOW_FIT,
    OpportunityLifecycleState.CLOSED_DUPLICATE,
}

ACTIVE_PIPELINE_STATES: Final[set[OpportunityLifecycleState]] = {
    OpportunityLifecycleState.MATERIALS_READY,
    OpportunityLifecycleState.APPLIED,
    OpportunityLifecycleState.FOLLOW_UP_DUE,
}

ALLOWED_TRANSITIONS: Final[TransitionMap] = {
    OpportunityLifecycleState.SOURCED: (
        OpportunityLifecycleState.NORMALIZED,
        OpportunityLifecycleState.CLOSED_DUPLICATE,
    ),
    OpportunityLifecycleState.NORMALIZED: (
        OpportunityLifecycleState.COMPANY_RESEARCHED,
        OpportunityLifecycleState.CLOSED_DUPLICATE,
    ),
    OpportunityLifecycleState.COMPANY_RESEARCHED: (
        OpportunityLifecycleState.FIT_SCORED,
        OpportunityLifecycleState.CLOSED_LOW_FIT,
    ),
    OpportunityLifecycleState.FIT_SCORED: (
        OpportunityLifecycleState.MATERIALS_READY,
        OpportunityLifecycleState.CLOSED_LOW_FIT,
    ),
    OpportunityLifecycleState.MATERIALS_READY: (OpportunityLifecycleState.APPLIED,),
    OpportunityLifecycleState.APPLIED: (
        OpportunityLifecycleState.FOLLOW_UP_DUE,
        OpportunityLifecycleState.CLOSED_REJECTED,
    ),
    OpportunityLifecycleState.FOLLOW_UP_DUE: (
        OpportunityLifecycleState.APPLIED,
        OpportunityLifecycleState.CLOSED_REJECTED,
    ),
    OpportunityLifecycleState.CLOSED_REJECTED: (),
    OpportunityLifecycleState.CLOSED_LOW_FIT: (),
    OpportunityLifecycleState.CLOSED_DUPLICATE: (),
}


class InvalidOpportunityTransition(ValueError):
    """Raised when an opportunity state transition is not allowed."""


class OpportunityRecord(BaseModel):
    source: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    state: OpportunityLifecycleState = OpportunityLifecycleState.SOURCED
    url: HttpUrl | None = None
    description: str = ""
    location: str | None = None
    compensation: str | None = None
    fit_score: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def next_action(self) -> str:
        return derive_next_action(self.state)


def derive_next_action(state: OpportunityLifecycleState) -> str:
    return NEXT_ACTIONS[state]


def allowed_next_states(
    state: OpportunityLifecycleState,
) -> tuple[OpportunityLifecycleState, ...]:
    return ALLOWED_TRANSITIONS[state]


def transition_opportunity(
    opportunity: OpportunityRecord,
    next_state: OpportunityLifecycleState,
) -> OpportunityRecord:
    allowed = allowed_next_states(opportunity.state)
    if next_state not in allowed:
        allowed_states = ", ".join(state.value for state in allowed) or "none"
        raise InvalidOpportunityTransition(
            f"Invalid transition {opportunity.state.value} -> {next_state.value}. "
            f"Allowed transitions: {allowed_states}."
        )
    return opportunity.model_copy(update={"state": next_state})


def filter_active_pipeline(
    opportunities: list[OpportunityRecord],
) -> list[OpportunityRecord]:
    return [
        opportunity
        for opportunity in opportunities
        if opportunity.state in ACTIVE_PIPELINE_STATES and opportunity.state not in CLOSED_STATES
    ]


async def _state_step(
    ctx: StepContext[None, None, OpportunityLifecycleState],
) -> OpportunityLifecycleState:
    return ctx.inputs


def build_opportunity_lifecycle_graph() -> Graph[
    None,
    None,
    OpportunityLifecycleState,
    OpportunityLifecycleState,
]:
    builder = GraphBuilder[
        None,
        None,
        OpportunityLifecycleState,
        OpportunityLifecycleState,
    ](
        name="opportunity_lifecycle",
        state_type=None,
        deps_type=None,
        input_type=OpportunityLifecycleState,
        output_type=OpportunityLifecycleState,
        auto_instrument=False,
    )
    nodes = {
        state: builder.step(_state_step, node_id=state.value, label=state.value)
        for state in OpportunityLifecycleState
    }

    builder.add_edge(builder.start_node, nodes[OpportunityLifecycleState.SOURCED], label="ingest")
    for from_state, to_states in ALLOWED_TRANSITIONS.items():
        for to_state in to_states:
            builder.add_edge(nodes[from_state], nodes[to_state])
    for state in CLOSED_STATES:
        builder.add_edge(nodes[state], builder.end_node, label="terminal")

    return builder.build()


def export_opportunity_lifecycle_mermaid() -> str:
    return build_opportunity_lifecycle_graph().render(
        title="Opportunity Lifecycle",
        direction="LR",
    )
