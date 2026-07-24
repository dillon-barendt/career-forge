"""Opportunity schema and lifecycle helpers."""

from career_ops.opportunities.lifecycle import (
    ACTIVE_PIPELINE_STATES,
    ALLOWED_TRANSITIONS,
    CLOSED_STATES,
    InvalidOpportunityTransition,
    OpportunityLifecycleState,
    OpportunityRecord,
    allowed_next_states,
    derive_next_action,
    export_opportunity_lifecycle_mermaid,
    filter_active_pipeline,
    transition_opportunity,
)

__all__ = [
    "ACTIVE_PIPELINE_STATES",
    "CLOSED_STATES",
    "ALLOWED_TRANSITIONS",
    "InvalidOpportunityTransition",
    "OpportunityLifecycleState",
    "OpportunityRecord",
    "allowed_next_states",
    "derive_next_action",
    "export_opportunity_lifecycle_mermaid",
    "filter_active_pipeline",
    "transition_opportunity",
]
