import re
from datetime import datetime
from pathlib import Path

from career_ops.compat import UTC, StrEnum


class Example(StrEnum):
    VALUE = "value"


def test_compat_exports_utc_and_string_enum() -> None:
    assert datetime(2026, 8, 24, tzinfo=UTC).isoformat().endswith("+00:00")
    assert str(Example.VALUE) == "value"
    assert Example.VALUE == "value"


def test_development_requirements_pin_ruff_to_lock_version() -> None:
    lock_text = Path("uv.lock").read_text(encoding="utf-8")
    package_blocks = re.findall(
        r"(?ms)^\[\[package\]\]\n(.*?)(?=^\[\[package\]\]\n|\Z)",
        lock_text,
    )
    ruff_versions = [
        match.group(1)
        for block in package_blocks
        if re.search(r'^name = "ruff"$', block, flags=re.MULTILINE)
        if (match := re.search(r'^version = "([^"]+)"$', block, flags=re.MULTILINE))
    ]
    requirement_lines = {
        line.strip()
        for line in Path("requirements-dev.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    ruff_requirements = {
        line for line in requirement_lines if re.match(r"(?i)^ruff(?:\s|\[|[<>=!~;@]|$)", line)
    }

    assert len(ruff_versions) == 1
    assert ruff_requirements == {f"ruff=={ruff_versions[0]}"}
