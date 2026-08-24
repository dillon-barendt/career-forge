"""Build versioned AI prompts and parse their structured responses."""

import json

from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)

EMAIL_CLASSIFIER_PROMPT_VERSION: str = "email-classifier-v1"
OPPORTUNITY_EVALUATOR_PROMPT_VERSION: str = "opportunity-evaluator-v1"


def build_email_classifier_prompt(message: EmailMessage) -> str:
    """Serialize an email message into the versioned classifier prompt."""
    payload = {
        "prompt_version": EMAIL_CLASSIFIER_PROMPT_VERSION,
        "message_id": message.message_id,
        "thread_id": message.thread_id,
        "sender": message.sender,
        "recipients": message.recipients,
        "subject": message.subject,
        "body": message.body,
        "received_at": message.received_at.isoformat(),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def build_opportunity_evaluator_prompt(posting: JobPosting) -> str:
    """Serialize a job posting into the versioned evaluator prompt."""
    payload = {
        "prompt_version": OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
        "posting": posting.model_dump(mode="json"),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def parse_email_classifier_output(output: object) -> PydanticAIEmailEvaluation:
    """Validate an email classifier response as its typed evaluation."""
    if isinstance(output, PydanticAIEmailEvaluation):
        return output
    return PydanticAIEmailEvaluation.model_validate(output)


def parse_opportunity_evaluator_output(output: object) -> OpportunityEvaluation:
    """Validate an opportunity evaluator response as its typed evaluation."""
    if isinstance(output, OpportunityEvaluation):
        return output
    return OpportunityEvaluation.model_validate(output)
