from datetime import date

from career_ops.analytics.weekly import WeeklyAnalyticsInput, generate_weekly_analytics
from career_ops.models import AnalyticsApplication, AnalyticsContact, ApplicationStage


def test_weekly_analytics_calculates_rates_and_recommendations() -> None:
    analytics = generate_weekly_analytics(
        WeeklyAnalyticsInput(
            week_start=date(2026, 7, 6),
            applications=[
                AnalyticsApplication(
                    company="Acme",
                    source="LinkedIn",
                    stage=ApplicationStage.SUBMITTED,
                    submitted_on=date(2026, 7, 6),
                    first_response_on=date(2026, 7, 8),
                ),
                AnalyticsApplication(
                    company="Beta",
                    source="Recruiter",
                    stage=ApplicationStage.INTERVIEWING,
                    submitted_on=date(2026, 7, 7),
                    first_response_on=date(2026, 7, 8),
                ),
            ],
            contacts=[
                AnalyticsContact(name="Sam", contacted_on=date(2026, 7, 6), responded=True),
                AnalyticsContact(name="Lee", contacted_on=date(2026, 7, 6), responded=False),
            ],
        )
    )

    assert analytics.applications_submitted == 2
    assert analytics.response_rate == 1.0
    assert analytics.interview_rate == 0.5
    assert analytics.recruiter_response_rate == 0.5
    assert analytics.average_time_to_response_days == 1.5
    assert analytics.weekly_recommendations
