import pytest
from career_ops.cli import app
from career_ops.opportunities.lifecycle import (
    ACTIVE_PIPELINE_STATES,
    InvalidOpportunityTransition,
    OpportunityLifecycleState,
    OpportunityRecord,
    derive_next_action,
    export_opportunity_lifecycle_mermaid,
    filter_active_pipeline,
    transition_opportunity,
)
from pydantic import ValidationError
from typer.testing import CliRunner


def test_opportunity_record_defines_required_fields() -> None:
    with pytest.raises(ValidationError):
        OpportunityRecord.model_validate({"title": "Backend Engineer"})

    opportunity = OpportunityRecord(
        source="lever",
        source_id="job_123",
        title="Backend Engineer",
        company="Acme",
    )

    assert opportunity.state == OpportunityLifecycleState.SOURCED
    assert opportunity.next_action == derive_next_action(OpportunityLifecycleState.SOURCED)


def test_lifecycle_allows_expected_progression_and_derives_next_action() -> None:
    opportunity = OpportunityRecord(
        source="lever",
        source_id="job_123",
        title="Backend Engineer",
        company="Acme",
    )

    for expected_state in (
        OpportunityLifecycleState.NORMALIZED,
        OpportunityLifecycleState.COMPANY_RESEARCHED,
        OpportunityLifecycleState.FIT_SCORED,
        OpportunityLifecycleState.MATERIALS_READY,
        OpportunityLifecycleState.APPLIED,
        OpportunityLifecycleState.FOLLOW_UP_DUE,
    ):
        opportunity = transition_opportunity(opportunity, expected_state)
        assert opportunity.state == expected_state
        assert opportunity.next_action == derive_next_action(expected_state)


def test_invalid_transition_is_documented_in_error() -> None:
    opportunity = OpportunityRecord(
        source="manual",
        source_id="job_123",
        title="Backend Engineer",
        company="Acme",
    )

    with pytest.raises(InvalidOpportunityTransition) as exc_info:
        transition_opportunity(opportunity, OpportunityLifecycleState.APPLIED)

    message = str(exc_info.value)
    assert "sourced -> applied" in message
    assert "Allowed transitions: normalized, closed_duplicate" in message


def test_duplicate_and_low_fit_records_are_filtered_before_active_pipeline() -> None:
    duplicate = OpportunityRecord(
        source="lever",
        source_id="dup",
        title="Backend Engineer",
        company="Acme",
        state=OpportunityLifecycleState.CLOSED_DUPLICATE,
    )
    low_fit = duplicate.model_copy(
        update={"source_id": "low", "state": OpportunityLifecycleState.CLOSED_LOW_FIT}
    )
    ready = duplicate.model_copy(
        update={"source_id": "ready", "state": OpportunityLifecycleState.MATERIALS_READY}
    )

    assert {
        OpportunityLifecycleState.MATERIALS_READY,
        OpportunityLifecycleState.APPLIED,
        OpportunityLifecycleState.FOLLOW_UP_DUE,
    } == ACTIVE_PIPELINE_STATES
    assert filter_active_pipeline([duplicate, low_fit, ready]) == [ready]


def test_lifecycle_exports_mermaid_state_graph() -> None:
    mermaid = export_opportunity_lifecycle_mermaid()

    assert "stateDiagram-v2" in mermaid
    assert "title: Opportunity Lifecycle" in mermaid
    assert "sourced: sourced" in mermaid
    assert "normalized: normalized" in mermaid
    assert "closed_duplicate: closed_duplicate" in mermaid
    assert "closed_low_fit: closed_low_fit" in mermaid
    assert "--> normalized" in mermaid
    assert "--> closed_duplicate" in mermaid
    assert "--> closed_low_fit" in mermaid
    assert "materials_ready --> applied" in mermaid


def test_cli_outputs_lifecycle_mermaid_graph() -> None:
    result = CliRunner().invoke(app, ["opportunity-lifecycle", "--mermaid"])

    assert result.exit_code == 0
    assert "stateDiagram-v2" in result.stdout
    assert "materials_ready --> applied" in result.stdout
