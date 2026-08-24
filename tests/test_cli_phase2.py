from typer.testing import CliRunner

from career_ops.cli import app


def test_today_command_shows_three_action_sections() -> None:
    result = CliRunner().invoke(app, ["today"])

    assert result.exit_code == 0
    assert "Career Forge Today" in result.stdout
    assert "Follow up" in result.stdout
    assert "Review" in result.stdout
    assert "Apply" in result.stdout
