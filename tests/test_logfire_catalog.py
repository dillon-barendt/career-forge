from pathlib import Path

from career_ops.logfire_catalog import emit_logfire_catalog, full_catalog


class FakeObservability:
    def __init__(self) -> None:
        self.infos = []
        self.metrics = []

    def info(self, event_name: str, **attributes) -> None:
        self.infos.append((event_name, attributes))

    def increment(self, metric_name: str, **attributes) -> None:
        self.metrics.append((metric_name, attributes))


def test_full_catalog_includes_agents_prompts_llms_and_providers(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompts"
    phase3 = prompt_root / "phase3"
    phase3.mkdir(parents=True)
    (phase3 / "email_classifier_v1.md").write_text("Classify this email.", encoding="utf-8")

    items = full_catalog(prompt_root)
    by_kind = {item.kind for item in items}
    names = {item.name for item in items}

    assert by_kind == {"agent", "prompt", "llm", "provider"}
    assert "gmail" in names
    assert "email-classifier-v1" in names
    assert "gateway/openai:gpt-5.2" in names
    assert "logfire" in names


def test_emit_logfire_catalog_records_structured_metadata(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    (prompt_root / "followup.md").write_text("Draft follow-up.", encoding="utf-8")
    observability = FakeObservability()

    items = emit_logfire_catalog(observability, prompt_root=prompt_root)

    assert len(observability.infos) == len(items)
    assert len(observability.metrics) == len(items)
    assert ("career_forge.catalog.items", {"catalog_kind": "prompt", "status": "available"}) in (
        observability.metrics
    )
    event_name, attributes = observability.infos[0]
    assert event_name.startswith("career_ops.catalog.")
    expected_keys = {
        "catalog_kind",
        "name",
        "version",
        "owner",
        "status",
        "description",
        "path",
        "tags",
    }
    assert expected_keys <= attributes.keys()
