import sys
from types import SimpleNamespace

from career_ops.config import Settings
from career_ops.observability import Observability


class FakeAdvancedOptions:
    def __init__(self, *, base_url: str) -> None:
        self.base_url = base_url


class FakeVariablesOptions:
    def __init__(self, *, block_before_first_resolve: bool) -> None:
        self.block_before_first_resolve = block_before_first_resolve


class FakeMetric:
    def __init__(self) -> None:
        self.values = []

    def add(self, value, attributes=None) -> None:
        self.values.append((value, attributes))

    def record(self, value, attributes=None) -> None:
        self.values.append((value, attributes))


class FakeVariable:
    def __init__(self, default) -> None:
        self.default = default

    def get(self, **kwargs):
        variable = self

        class Resolved:
            value = variable.default

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        return Resolved()


class FakeLogfire(SimpleNamespace):
    AdvancedOptions = FakeAdvancedOptions
    VariablesOptions = FakeVariablesOptions

    def __init__(self) -> None:
        super().__init__()
        self.configure_kwargs = None
        self.instrument_kwargs = None
        self.openai_instrumented = False
        self.httpx_instrumented = False
        self.system_metrics_instrumented = False
        self.fastapi_instrumented = False
        self.metrics = {}
        self.variables = {}

    def configure(self, **kwargs) -> None:
        self.configure_kwargs = kwargs

    def instrument_pydantic_ai(self, **kwargs) -> None:
        self.instrument_kwargs = kwargs

    def instrument_openai(self) -> None:
        self.openai_instrumented = True

    def instrument_httpx(self, **kwargs) -> None:
        self.httpx_instrumented = True

    def instrument_system_metrics(self) -> None:
        self.system_metrics_instrumented = True

    def instrument_fastapi(self, app, **kwargs) -> None:
        self.fastapi_instrumented = True

    def metric_counter(self, name: str, **kwargs):
        self.metrics[name] = FakeMetric()
        return self.metrics[name]

    def metric_histogram(self, name: str, **kwargs):
        self.metrics[name] = FakeMetric()
        return self.metrics[name]

    def var(self, name: str, *, default, **kwargs):
        self.variables[name] = FakeVariable(default)
        return self.variables[name]


def test_observability_configures_target_logfire_project(monkeypatch) -> None:
    fake_logfire = FakeLogfire()
    monkeypatch.setitem(sys.modules, "logfire", fake_logfire)
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-token")

    settings = Settings(logfire_environment="test")
    Observability(settings).configure()

    assert settings.logfire_token is not None
    assert settings.logfire_token.get_secret_value() == "test-token"
    assert fake_logfire.configure_kwargs["token"] == "test-token"
    assert fake_logfire.configure_kwargs["service_name"] == "career-forge"
    assert fake_logfire.configure_kwargs["environment"] == "test"
    assert fake_logfire.configure_kwargs["advanced"].base_url == "https://logfire-us.pydantic.dev"
    assert fake_logfire.configure_kwargs["variables"].block_before_first_resolve is False
    assert fake_logfire.instrument_kwargs == {
        "include_binary_content": False,
        "include_content": False,
    }
    assert fake_logfire.openai_instrumented is True
    assert fake_logfire.httpx_instrumented is True
    assert "career_forge.ai.requests" in fake_logfire.metrics
    assert "career_forge.ai.gateway_enabled" in fake_logfire.variables


def test_observability_is_non_interactive_without_token(monkeypatch) -> None:
    fake_logfire = FakeLogfire()
    monkeypatch.setitem(sys.modules, "logfire", fake_logfire)
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)

    Observability(Settings()).configure()

    assert fake_logfire.configure_kwargs["send_to_logfire"] == "if-token-present"


def test_observability_records_metrics_and_resolves_variables(monkeypatch) -> None:
    fake_logfire = FakeLogfire()
    monkeypatch.setitem(sys.modules, "logfire", fake_logfire)

    observability = Observability(Settings())
    observability.configure()
    observability.increment("career_forge.ai.requests", agent_name="email_classifier")
    observability.record("career_forge.ai.confidence", 0.9, agent_name="email_classifier")

    assert fake_logfire.metrics["career_forge.ai.requests"].values
    assert fake_logfire.metrics["career_forge.ai.confidence"].values
    assert observability.resolve_bool("career_forge.ai.gateway_enabled", False) is False
