from career_ops.ai.prompts import EMAIL_CLASSIFIER_PROMPT_VERSION
from career_ops.models import (
    EmailCategory,
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)
from career_ops.notion.schemas import JobOpportunity
from career_ops.scoring.fit_score import score_opportunity
from career_ops.scoring.rules import normalize_text

DETERMINISTIC_MODEL = "deterministic:rules-v1"


class DeterministicAIService:
    """Produces reproducible career decisions from versioned local rules."""

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        text = normalize_text(f"{message.subject} {message.body} {message.sender}")
        category = EmailCategory.COMPANY_COMMUNICATION
        confidence = 0.55
        reason = "Local rules could not confidently classify this message."

        signals = (
            (
                EmailCategory.NEWSLETTER,
                0.95,
                "Newsletter signal detected.",
                "unsubscribe" in text or "newsletter" in text,
            ),
            (
                EmailCategory.OFFER,
                0.88,
                "Offer language detected.",
                "offer" in text and "letter" in text,
            ),
            (
                EmailCategory.INTERVIEW_INVITATION,
                0.9,
                "Interview scheduling language detected.",
                "interview" in text
                and any(
                    term in text for term in ("invite", "schedule", "availability", "available")
                ),
            ),
            (
                EmailCategory.REJECTION,
                0.9,
                "Rejection language detected.",
                any(term in text for term in ("not moving forward", "unfortunately", "declined")),
            ),
            (
                EmailCategory.INTERVIEW_CONFIRMATION,
                0.86,
                "Interview confirmation language detected.",
                "interview" in text and any(term in text for term in ("confirmed", "calendar")),
            ),
            (
                EmailCategory.APPLICATION_CONFIRMATION,
                0.86,
                "Application confirmation language detected.",
                any(term in text for term in ("application received", "thank you for applying")),
            ),
            (
                EmailCategory.RECRUITER_FOLLOW_UP,
                0.78,
                "Recruiter follow-up language detected.",
                any(term in text for term in ("following up", "circling back", "checking in")),
            ),
            (
                EmailCategory.RECRUITER_OUTREACH,
                0.72,
                "Recruiter or opportunity language detected.",
                any(term in text for term in ("recruiter", "talent", "opportunity", "role")),
            ),
        )
        for signal_category, signal_confidence, signal_reason, matched in signals:
            if matched:
                category = signal_category
                confidence = signal_confidence
                reason = signal_reason
                break

        return PydanticAIEmailEvaluation(
            classification=category,
            confidence_score=confidence,
            executive_summary=f"Email classified as {category.value}.",
            suggested_next_action="Review or process according to classification.",
            human_review_required=confidence < 0.65,
            reasons=[reason],
            prompt_version=EMAIL_CLASSIFIER_PROMPT_VERSION,
            model_name=DETERMINISTIC_MODEL,
            fallback_status="deterministic",
        )

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        opportunity = JobOpportunity(
            title=posting.role,
            company=posting.company,
            description=posting.description,
            location=posting.location,
            compensation=posting.compensation,
            source=posting.provider,
            tags=[*posting.skills, *posting.tech_stack],
        )
        fit = score_opportunity(opportunity)
        confidence = self._posting_confidence(posting)
        concerns = fit.concerns.copy()
        if not posting.compensation:
            concerns.append("Compensation was not detected in the posting.")
        return OpportunityEvaluation(
            executive_summary=(
                f"{posting.role} at {posting.company} scored {fit.score}/100 "
                "using the deterministic evaluator."
            ),
            fit_score=fit.score,
            confidence_score=confidence,
            match_analysis=self._match_analysis(fit.score),
            strengths=fit.strengths or ["Posting includes enough detail for review."],
            potential_concerns=concerns,
            missing_qualifications=[],
            resume_suggestions=[f"Mirror the target title: {posting.role}."],
            cover_letter_talking_points=[
                f"Connect prior software engineering impact to {posting.company}."
            ],
            interview_preparation_topics=["Prepare a project walkthrough with tradeoffs."],
            suggested_next_action=fit.recommended_action,
        )

    def evaluate_opportunity(self, posting: JobPosting) -> OpportunityEvaluation:
        return self.evaluate(posting)

    @staticmethod
    def _posting_confidence(posting: JobPosting) -> float:
        fields = [
            bool(posting.company),
            bool(posting.role),
            bool(posting.description),
            bool(posting.location or posting.remote_policy),
            bool(posting.skills),
            bool(posting.apply_url),
        ]
        return round((sum(fields) / len(fields)) * 100, 2)

    @staticmethod
    def _match_analysis(fit_score: int) -> str:
        if fit_score >= 75:
            return "Strong match. Prioritize application and recruiter outreach."
        if fit_score >= 55:
            return "Possible match. Review missing details before applying."
        return "Weak match. Archive unless strategically valuable."
