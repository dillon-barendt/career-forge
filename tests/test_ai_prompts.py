import json

import pytest
from pydantic import ValidationError

from career_ops.ai import prompts
from career_ops.ai.prompts import (
    EMAIL_CLASSIFIER_PROMPT_VERSION,
    OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
    build_email_classifier_prompt,
    build_opportunity_evaluator_prompt,
    parse_email_classifier_output,
    parse_opportunity_evaluator_output,
)
from career_ops.models import EmailMessage, JobPosting


def test_prompt_versions_are_public_str_constants() -> None:
    assert prompts.__annotations__["EMAIL_CLASSIFIER_PROMPT_VERSION"] is str
    assert prompts.__annotations__["OPPORTUNITY_EVALUATOR_PROMPT_VERSION"] is str


def test_email_prompt_is_versioned_stable_json() -> None:
    message = EmailMessage(
        message_id="prompt-1",
        thread_id="thread-1",
        sender="Recruiter <recruiter@example.com>",
        recipients=["candidate@example.com"],
        subject="Interview invitation",
        body="Please send availability.",
        received_at="2026-08-24T12:00:00Z",
    )

    payload = json.loads(build_email_classifier_prompt(message))

    assert payload["prompt_version"] == EMAIL_CLASSIFIER_PROMPT_VERSION
    assert payload["message_id"] == message.message_id
    assert payload["subject"] == message.subject


def test_email_parser_rejects_invalid_structured_output() -> None:
    with pytest.raises(ValidationError):
        parse_email_classifier_output({"classification": "Offer"})


def test_opportunity_prompt_is_versioned_stable_json() -> None:
    posting = JobPosting(
        source_url="https://jobs.example.com/platform-engineer",
        provider="example",
        company="Example",
        role="Platform Engineer",
        description="Build reliable developer platforms.",
    )

    payload = json.loads(build_opportunity_evaluator_prompt(posting))

    assert payload["prompt_version"] == OPPORTUNITY_EVALUATOR_PROMPT_VERSION
    assert payload["posting"]["company"] == posting.company
    assert payload["posting"]["role"] == posting.role


def test_opportunity_parser_rejects_invalid_structured_output() -> None:
    with pytest.raises(ValidationError):
        parse_opportunity_evaluator_output({"fit_score": 85})
