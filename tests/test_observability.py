import sys
from types import SimpleNamespace

from career_ops.config import Settings
from career_ops.observability import Observability


class FakeAdvancedOptions:
    def __init__(self, *, base_url: str) -> None:
        self.base_url = base_url


class FakeLogfire(SimpleNamespace):
    AdvancedOptions = FakeAdvancedOptions

    def __init__(self) -> None:
        super().__init__()
        self.configure_kwargs = None
        self.instrument_kwargs = None

    def configure(self, **kwargs) -> None:
        self.configure_kwargs = kwargs

    def instrument_pydantic_ai(self, **kwargs) -> None:
        self.instrument_kwargs = kwargs


def test_observability_configures_target_logfire_project(monkeypatch) -> None:
    fake_logfire = FakeLogfire()
    monkeypatch.setitem(sys.modules, "logfire", fake_logfire)
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-token")

    settings = Settings(logfire_environment="test")
    Observability(settings).configure()

    assert settings.logfire_token is not None
    assert settings.logfire_token.get_secret_value() == "test-token"
    assert fake_logfire.configure_kwargs["token"] == "test-token"
    assert fake_logfire.configure_kwargs["service_name"] == "career-ops"
    assert fake_logfire.configure_kwargs["environment"] == "test"
    assert fake_logfire.configure_kwargs["advanced"].base_url == "https://logfire-us.pydantic.dev"
    assert fake_logfire.instrument_kwargs == {
        "include_binary_content": False,
        "include_content": False,
    }


def test_observability_is_non_interactive_without_token(monkeypatch) -> None:
    fake_logfire = FakeLogfire()
    monkeypatch.setitem(sys.modules, "logfire", fake_logfire)
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)

    Observability(Settings()).configure()

    assert fake_logfire.configure_kwargs["send_to_logfire"] == "if-token-present"
