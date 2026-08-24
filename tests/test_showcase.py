import json

import pytest

from career_ops.showcase.demo import main, render_human
from career_ops.showcase.runner import ShowcaseRunner


def test_showcase_runs_three_real_agent_scenarios() -> None:
    report = ShowcaseRunner().run()

    assert report.mode == "mock"
    assert [scenario.slug for scenario in report.scenarios] == [
        "triage-interview-email",
        "evaluate-platform-role",
        "tailor-resume",
    ]
    assert report.scenarios[0].result["classification"] == "Interview Invitation"
    assert report.scenarios[0].result["next_action"] == (
        "Reply with availability and create prep brief."
    )
    assert report.scenarios[1].result["provider"] == "lever"
    assert report.scenarios[1].result["priority"] == "High"
    assert report.scenarios[1].result["next_action"] == "prioritize"
    assert report.scenarios[2].result["kind"] == "resume_tailoring"
    assert "Principal Platform Engineer" in report.scenarios[2].result["preview"]


def test_showcase_does_not_load_live_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_settings_are_loaded() -> None:
        raise AssertionError("credential-free showcase loaded live settings")

    monkeypatch.setattr(
        "career_ops.ingestion.job_ingestion.get_settings",
        fail_if_settings_are_loaded,
    )
    monkeypatch.setattr(
        "career_ops.automation.gmail_ingestion.build_ai_service",
        fail_if_settings_are_loaded,
    )
    monkeypatch.setattr(
        "career_ops.ingestion.job_ingestion.build_ai_service",
        fail_if_settings_are_loaded,
    )

    assert ShowcaseRunner().run().mode == "mock"


def test_showcase_human_output_is_scannable() -> None:
    output = render_human(ShowcaseRunner().run())

    assert "CareerForge — mock agent demo" in output
    assert "1. Triage an interview invitation" in output
    assert "2. Evaluate a platform role" in output
    assert "3. Tailor the resume" in output
    assert "No credentials. No network calls. No writes." in output


def test_showcase_json_mode_returns_stable_typed_report(capsys) -> None:
    exit_code = main(["--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == "1.0"
    assert len(payload["scenarios"]) == 3
