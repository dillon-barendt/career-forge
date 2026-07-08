from career_ops.providers.jobs.generic import WorkdayJobProvider

WORKDAY_HTML = """
<html>
  <head>
    <title>Senior Backend Engineer</title>
    <meta property="og:site_name" content="Acme Careers" />
  </head>
  <body>
    <h1>Senior Backend Engineer</h1>
    <p>Location: Remote - United States</p>
    <p>We build Python and Postgres services.</p>
  </body>
</html>
"""


def test_workday_provider_extracts_company_from_site_metadata() -> None:
    posting = WorkdayJobProvider().extract(
        "https://acme.wd1.myworkdayjobs.com/en-US/acme/job/backend",
        WORKDAY_HTML,
    )

    assert posting.company == "Acme"
    assert posting.role == "Senior Backend Engineer"
    assert posting.remote_policy == "Remote"
