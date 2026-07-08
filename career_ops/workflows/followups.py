from datetime import date

from career_ops.notion.schemas import Application, ApplicationStatus


def due_followups(applications: list[Application], today: date | None = None) -> list[Application]:
    current_date = today or date.today()
    return [
        application
        for application in applications
        if application.follow_up_on is not None
        and application.follow_up_on <= current_date
        and application.status not in {ApplicationStatus.CLOSED, ApplicationStatus.OFFER}
    ]
