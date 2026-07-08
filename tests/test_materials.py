from career_ops.materials.recruiter_dm import build_recruiter_dm
from career_ops.materials.resume_tailor import build_resume_tailoring_notes
from career_ops.notion.schemas import JobOpportunity
from career_ops.workflows.interview_prep import build_interview_prep


def test_recruiter_dm_uses_contact_and_role() -> None:
    opportunity = JobOpportunity(title="Platform Engineer", company="Acme")

    draft = build_recruiter_dm(opportunity, contact_name="Sam")

    assert draft.kind == "recruiter_dm"
    assert "Hi Sam," in draft.body
    assert "Platform Engineer" in draft.body
    assert "Acme" in draft.body


def test_resume_tailoring_includes_description() -> None:
    opportunity = JobOpportunity(
        title="Backend Engineer",
        company="Acme",
        description="Own Python APIs and reliability work.",
    )

    draft = build_resume_tailoring_notes(opportunity)

    assert draft.kind == "resume_tailoring"
    assert "Own Python APIs" in draft.body


def test_interview_prep_has_questions() -> None:
    opportunity = JobOpportunity(title="Backend Engineer", company="Acme")

    draft = build_interview_prep(opportunity)

    assert "Questions to ask" in draft.body
    assert draft.company == "Acme"
