import argparse
from collections.abc import Sequence

from career_ops.showcase.runner import ShowcaseReport, ShowcaseRunner


def render_human(report: ShowcaseReport) -> str:
    """Renders the stable demo report for terminal viewers."""

    lines = [
        "CareerForge — mock agent demo",
        "AI agents that forge career data into action.",
        "",
    ]
    for index, scenario in enumerate(report.scenarios, start=1):
        lines.extend(
            [
                f"{index}. {scenario.title}",
                f"   prompt  {scenario.prompt}",
                f"   output  {_result_summary(scenario.result)}",
                "",
            ]
        )
    lines.append("No credentials. No network calls. No writes.")
    return "\n".join(lines)


def _result_summary(result: dict[str, str | int | float | bool]) -> str:
    return " · ".join(f"{key}={value}" for key, value in result.items())


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the mock showcase in human or JSON mode."""

    parser = argparse.ArgumentParser(description="Run the CareerForge agent showcase.")
    parser.add_argument("--json", action="store_true", help="Print the typed report as JSON.")
    args = parser.parse_args(argv)
    report = ShowcaseRunner().run()
    print(report.model_dump_json(indent=2) if args.json else render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
