from collections import Counter

from career_ops.models import ApplicationStage, WeeklyAnalytics, WeeklyAnalyticsInput


def generate_weekly_analytics(data: WeeklyAnalyticsInput) -> WeeklyAnalytics:
    applications = data.applications
    contacts = data.contacts
    applications_submitted = len(applications)
    responses = [app for app in applications if app.first_response_on is not None]
    interviews = [
        app
        for app in applications
        if app.stage in {ApplicationStage.INTERVIEWING, ApplicationStage.OFFER}
    ]
    offers = [app for app in applications if app.stage == ApplicationStage.OFFER]

    response_days = [
        (app.first_response_on - app.submitted_on).days
        for app in responses
        if app.first_response_on is not None
    ]
    recruiter_responses = [contact for contact in contacts if contact.responded]

    return WeeklyAnalytics(
        applications_submitted=applications_submitted,
        response_rate=_rate(len(responses), applications_submitted),
        interview_rate=_rate(len(interviews), applications_submitted),
        offer_rate=_rate(len(offers), applications_submitted),
        pipeline_conversion=Counter(app.stage.value for app in applications),
        average_time_to_response_days=_average(response_days),
        recruiter_response_rate=_rate(len(recruiter_responses), len(contacts)),
        source_effectiveness=Counter(app.source for app in applications),
        company_activity=Counter(app.company for app in applications),
        weekly_recommendations=_recommendations(
            applications_submitted=applications_submitted,
            response_rate=_rate(len(responses), applications_submitted),
            interview_rate=_rate(len(interviews), applications_submitted),
            recruiter_response_rate=_rate(len(recruiter_responses), len(contacts)),
        ),
    )


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 2)


def _average(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _recommendations(
    *,
    applications_submitted: int,
    response_rate: float,
    interview_rate: float,
    recruiter_response_rate: float,
) -> list[str]:
    recommendations: list[str] = []
    if applications_submitted < 5:
        recommendations.append("Increase high-fit applications before optimizing the funnel.")
    if response_rate < 0.3:
        recommendations.append("Review resume targeting and source mix; response rate is low.")
    if interview_rate < 0.2:
        recommendations.append("Prioritize recruiter conversations and referrals.")
    if recruiter_response_rate < 0.4:
        recommendations.append("Tighten recruiter outreach and follow-up cadence.")
    if not recommendations:
        recommendations.append("Keep current cadence and focus on interview preparation.")
    return recommendations
