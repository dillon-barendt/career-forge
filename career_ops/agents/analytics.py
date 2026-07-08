from career_ops.analytics.weekly import generate_weekly_analytics
from career_ops.models import WeeklyAnalytics, WeeklyAnalyticsInput


class AnalyticsAgent:
    name = "Analytics Agent"

    def weekly(self, data: WeeklyAnalyticsInput) -> WeeklyAnalytics:
        return generate_weekly_analytics(data)
