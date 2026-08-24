# CareerForge Mock-Mode Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit mock-versus-real AI runtime, broaden Python support, harden provider boundaries, and emit the evaluator's exact benchmark contract without weakening the existing showcase.

**Architecture:** A single factory selects a typed `CareerAIService` from validated settings. The live Pydantic AI adapter and configurable mock adapter share prompt codecs and domain protocols; application pipelines consume those protocols and carry provider metadata explicitly in domain results.

**Tech Stack:** Python 3.10-3.12, Pydantic v2, Pydantic Settings, Pydantic AI, pytest, pytest-cov, Ruff, Pyright, uv, Docker, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-24-mock-mode-hardening-design.md`

## Global Constraints

- Preserve the repository name `dillon-barendt/career-forge`, distribution name `career-forge`, CLI command `career-forge`, and product name `CareerForge`.
- Support and test Python 3.10, 3.11, and 3.12.
- `CAREER_FORGE_MODE` accepts exactly `mock` or `real` and defaults to `mock`.
- Mock mode performs no network calls and requires no credentials.
- Real mode must surface actionable configuration failures at the provider boundary.
- Retain Pydantic v2 models, deterministic rules, prompt versions, dry-run-first mutation controls, and 80 percent core coverage.
- Docker continues to install from `uv.lock` and run as a non-root user.
- The public benchmark JSON contains only the required top-level fields and required detail fields.
- Do not exercise live Gmail, Notion, Calendar, or hosted-model APIs in tests or CI.

---

## File Structure

### New files

- `career_ops/compat.py`: Python 3.10-compatible `UTC` and `StrEnum` definitions.
- `career_ops/ai/factory.py`: the only default AI service construction path.
- `career_ops/ai/mock.py`: configurable, protocol-compatible mock AI adapter.
- `career_ops/ai/prompts.py`: prompt serialization, prompt versions, and typed output parsing.
- `requirements-dev.txt`: pip-compatible development installation entrypoint.
- `tests/fixtures/__init__.py`: fixture package marker.
- `tests/fixtures/mock_llm.py`: reusable mock AI builders and canned typed outputs.
- `tests/test_ai_factory.py`: runtime-mode, factory, and mock adapter tests.
- `tests/test_ai_prompts.py`: prompt and parsing contract tests.
- `tests/test_compat.py`: Python compatibility behavior tests.
- `tests/test_mock_integration.py`: orchestrator/Gmail/Notion/ATS mock-boundary integration tests.

### Modified files

- `pyproject.toml`, `uv.lock`: Python floor, tool targets, version, and dependency lock.
- Nine modules importing `datetime.UTC` or `enum.StrEnum`: use `career_ops.compat`.
- `career_ops/config.py`: validated runtime mode.
- `career_ops/ai/contracts.py`: combined `CareerAIService` protocol.
- `career_ops/ai/deterministic.py`, `career_ops/ai/pydantic_ai_service.py`: shared prompt constants/codecs.
- `career_ops/automation/gmail_ingestion.py`, `career_ops/ingestion/job_ingestion.py`: factory-backed defaults.
- `career_ops/models/__init__.py`: explicit model/fallback metadata on classifications.
- `career_ops/gmail/sync.py`, `career_ops/gmail/single_message.py`: consume typed metadata.
- `career_ops/showcase/runner.py`, showcase tests: explicit mock demo semantics.
- `benchmark/bench.py`, benchmark tests/results: exact evaluator schema.
- `.github/workflows/ci.yml`, `Dockerfile`, `.env.example`: explicit mock mode and Python matrix.
- Public documentation and release metadata listed in Task 6.

---

### Task 1: Python 3.10 Compatibility and Development Install Contract

**Files:**
- Create: `career_ops/compat.py`
- Create: `requirements-dev.txt`
- Create: `tests/test_compat.py`
- Modify: `pyproject.toml`
- Modify: `career_ops/analytics/feedback_loop.py`
- Modify: `career_ops/evals/runner.py`
- Modify: `career_ops/gmail/client.py`
- Modify: `career_ops/models/__init__.py`
- Modify: `career_ops/models/webhooks.py`
- Modify: `career_ops/notion/schemas.py`
- Modify: `career_ops/opportunities/lifecycle.py`
- Modify: `career_ops/setup_validation.py`
- Modify: `career_ops/showcase/runner.py`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `career_ops.compat.UTC: datetime.tzinfo`
- Produces: `career_ops.compat.StrEnum`, a Python 3.10-compatible string enum base.
- Produces: `requirements-dev.txt` installable with `python -m pip install -r requirements-dev.txt`.

- [ ] **Step 1: Write failing compatibility tests**

```python
from datetime import datetime

from career_ops.compat import UTC, StrEnum


class Example(StrEnum):
    VALUE = "value"


def test_compat_exports_utc_and_string_enum() -> None:
    assert datetime(2026, 8, 24, tzinfo=UTC).isoformat().endswith("+00:00")
    assert str(Example.VALUE) == "value"
    assert Example.VALUE == "value"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_compat.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'career_ops.compat'`.

- [ ] **Step 3: Add the minimal compatibility module**

```python
from datetime import timezone
from enum import Enum

UTC = timezone.utc


class StrEnum(str, Enum):
    """Provides string-valued enum behavior on every supported Python version."""

    def __str__(self) -> str:
        return str(self.value)
```

- [ ] **Step 4: Replace 3.11-only imports**

In each listed module, import `UTC` and/or `StrEnum` from `career_ops.compat`
and remove the corresponding `datetime.UTC` or `enum.StrEnum` import. Preserve
all enum values and datetime behavior.

- [ ] **Step 5: Lower tool and package targets and add the pip entrypoint**

Update `pyproject.toml`:

```toml
requires-python = ">=3.10"

[tool.ruff]
target-version = "py310"

[tool.pyright]
pythonVersion = "3.10"
```

Create `requirements-dev.txt`:

```text
-e .[dev]
```

- [ ] **Step 6: Refresh the lock and run compatibility checks**

Run:

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv lock
UV_CACHE_DIR=/tmp/careerforge-uv uv run pytest tests/test_compat.py -q
UV_CACHE_DIR=/tmp/careerforge-uv uv run ruff check career_ops tests/test_compat.py
```

Expected: test passes and Ruff reports no errors.

- [ ] **Step 7: Verify the lower-bound interpreter**

Run:

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv run --python 3.10 python -c "import career_ops; from career_ops.compat import UTC, StrEnum; print(career_ops.__version__)"
```

Expected: exits 0 under Python 3.10.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock requirements-dev.txt career_ops/compat.py career_ops tests/test_compat.py
git commit -m "build: support Python 3.10 through 3.12"
```

---

### Task 2: Runtime Mode, Combined Protocol, Factory, and Mock AI Adapter

**Files:**
- Create: `career_ops/ai/factory.py`
- Create: `career_ops/ai/mock.py`
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/mock_llm.py`
- Create: `tests/test_ai_factory.py`
- Modify: `career_ops/ai/contracts.py`
- Modify: `career_ops/config.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `RuntimeMode.MOCK` and `RuntimeMode.REAL`.
- Produces: `CareerAIService(EmailClassificationService, OpportunityEvaluationService, Protocol)`.
- Produces: `MockAIService(email_results=..., opportunity_results=..., fallback=...)`.
- Produces: `build_ai_service(settings: Settings | None = None) -> CareerAIService`.

- [ ] **Step 1: Write failing settings and factory tests**

```python
import pytest
from pydantic import ValidationError

from career_ops.ai.factory import AIConfigurationError, build_ai_service
from career_ops.ai.mock import MockAIService
from career_ops.config import RuntimeMode, Settings


def test_settings_default_to_mock_mode() -> None:
    assert Settings(_env_file=None).mode is RuntimeMode.MOCK


def test_settings_reject_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mode="automatic")


def test_factory_builds_mock_without_credentials() -> None:
    service = build_ai_service(Settings(_env_file=None, mode="mock"))
    assert isinstance(service, MockAIService)


def test_real_openai_mode_requires_credentials() -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        openai_api_key=None,
    )
    with pytest.raises(AIConfigurationError, match="CAREER_FORGE_OPENAI_API_KEY"):
        build_ai_service(settings)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_ai_factory.py -q`

Expected: collection fails because factory, mock, and runtime mode do not exist.

- [ ] **Step 3: Add runtime mode and combined protocol**

```python
class RuntimeMode(StrEnum):
    MOCK = "mock"
    REAL = "real"


class CareerAIService(
    EmailClassificationService,
    OpportunityEvaluationService,
    Protocol,
):
    """Supports every typed AI decision required by career workflows."""
```

Add to `Settings`:

```python
mode: RuntimeMode = Field(default=RuntimeMode.MOCK, validation_alias=env_alias("MODE"))
```

- [ ] **Step 4: Implement the configurable mock adapter**

```python
EmailMockResult = PydanticAIEmailEvaluation | Exception
OpportunityMockResult = OpportunityEvaluation | Exception


class MockAIService:
    """Returns deterministic or test-controlled typed AI decisions without I/O."""

    model = "mock:deterministic-v1"

    def __init__(
        self,
        *,
        email_results: Mapping[str, EmailMockResult] | None = None,
        opportunity_results: Mapping[str, OpportunityMockResult] | None = None,
        fallback: DeterministicAIService | None = None,
    ) -> None:
        self.email_results = dict(email_results or {})
        self.opportunity_results = dict(opportunity_results or {})
        self.fallback = fallback or DeterministicAIService()

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        result = self.email_results.get(message.message_id)
        if isinstance(result, Exception):
            raise result
        if result is not None:
            return result.model_copy(
                update={"model_name": self.model, "fallback_status": "mock"}
            )
        return self.fallback.classify_email(message).model_copy(
            update={"model_name": self.model, "fallback_status": "mock"}
        )

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        key = str(posting.source_url)
        result = self.opportunity_results.get(key)
        if isinstance(result, Exception):
            raise result
        return result if result is not None else self.fallback.evaluate(posting)
```

- [ ] **Step 5: Implement factory validation and construction**

```python
class AIConfigurationError(RuntimeError):
    """Reports invalid real-provider configuration before model execution."""


def build_ai_service(settings: Settings | None = None) -> CareerAIService:
    resolved = settings or get_settings()
    if resolved.mode is RuntimeMode.MOCK:
        return MockAIService()
    if resolved.pydantic_ai_model.startswith("openai:"):
        if resolved.pydantic_ai_gateway_enabled:
            if resolved.pydantic_ai_gateway_api_key is None:
                raise AIConfigurationError(
                    "Real gateway mode requires CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY."
                )
        elif resolved.openai_api_key is None:
            raise AIConfigurationError(
                "Real OpenAI mode requires CAREER_FORGE_OPENAI_API_KEY."
            )
    return PydanticAIService(model=resolved.pydantic_ai_model, allow_local_fallback=False)
```

- [ ] **Step 6: Add reusable test fixtures**

`tests/fixtures/mock_llm.py` must export `mock_ai_service()` plus focused canned
email and opportunity result builders returning typed Pydantic models. Do not
return untyped dictionaries from the fixture.

- [ ] **Step 7: Add mock result and failure tests**

Test that an ID-specific result is returned, its metadata is normalized to
`mock`, an injected `RuntimeError("provider unavailable")` propagates, and an
unconfigured ID delegates to deterministic rules.

- [ ] **Step 8: Run focused tests and commit**

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv run pytest tests/test_ai_factory.py -q
UV_CACHE_DIR=/tmp/careerforge-uv uv run ruff check career_ops/ai career_ops/config.py tests/fixtures tests/test_ai_factory.py
git add career_ops/ai career_ops/config.py tests/fixtures tests/test_ai_factory.py .env.example
git commit -m "feat: add explicit mock and real AI modes"
```

---

### Task 3: Public Prompt Builders and Typed Parsers

**Files:**
- Create: `career_ops/ai/prompts.py`
- Create: `tests/test_ai_prompts.py`
- Modify: `career_ops/ai/pydantic_ai_service.py`
- Modify: `career_ops/ai/deterministic.py`
- Modify: `career_ops/ingestion/job_ingestion.py`
- Modify: `career_ops/evals/runner.py`
- Modify: tests importing prompt-version constants.

**Interfaces:**
- Produces: `EMAIL_CLASSIFIER_PROMPT_VERSION: str`.
- Produces: `OPPORTUNITY_EVALUATOR_PROMPT_VERSION: str`.
- Produces: `build_email_classifier_prompt(message: EmailMessage) -> str`.
- Produces: `build_opportunity_evaluator_prompt(posting: JobPosting) -> str`.
- Produces: `parse_email_classifier_output(output: object) -> PydanticAIEmailEvaluation`.
- Produces: `parse_opportunity_evaluator_output(output: object) -> OpportunityEvaluation`.

- [ ] **Step 1: Write failing prompt and parser tests**

```python
import json
import pytest
from pydantic import ValidationError

from career_ops.ai.prompts import (
    EMAIL_CLASSIFIER_PROMPT_VERSION,
    build_email_classifier_prompt,
    parse_email_classifier_output,
)
from career_ops.models import EmailMessage


def test_email_prompt_is_versioned_stable_json() -> None:
    message = EmailMessage(
        message_id="prompt-1",
        thread_id="thread-1",
        sender="Recruiter <recruiter@example.com>",
        recipients=["candidate@example.com"],
        subject="Interview invitation",
        body="Please send availability.",
        received_at="2026-08-24T12:00:00Z",
    )
    payload = json.loads(build_email_classifier_prompt(message))
    assert payload["prompt_version"] == EMAIL_CLASSIFIER_PROMPT_VERSION
    assert payload["message_id"] == message.message_id
    assert payload["subject"] == message.subject


def test_email_parser_rejects_invalid_structured_output() -> None:
    with pytest.raises(ValidationError):
        parse_email_classifier_output({"classification": "Offer"})
```

Add equivalent opportunity prompt and parser assertions.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai_prompts.py -q`

Expected: collection fails because `career_ops.ai.prompts` does not exist.

- [ ] **Step 3: Implement prompt builders and parsers**

Move the two version constants and current JSON payload logic from
`PydanticAIService` into the new module. Implement parsers as:

```python
def parse_email_classifier_output(output: object) -> PydanticAIEmailEvaluation:
    if isinstance(output, PydanticAIEmailEvaluation):
        return output
    return PydanticAIEmailEvaluation.model_validate(output)
```

Use the corresponding opportunity type for the second parser.

- [ ] **Step 4: Delegate from the live adapter**

Replace `_email_prompt`, `_opportunity_prompt`, and inline output coercion with
the public functions. Update deterministic, ingestion, eval, and test imports to
read constants from `career_ops.ai.prompts`. Delete the now-unused `json` import
and private prompt methods.

- [ ] **Step 5: Run focused and regression tests**

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv run pytest tests/test_ai_prompts.py tests/test_pydantic_ai_service.py tests/test_deterministic_ai_service.py -q
UV_CACHE_DIR=/tmp/careerforge-uv uv run pyright
```

Expected: all pass and Pyright reports zero errors.

- [ ] **Step 6: Commit**

```bash
git add career_ops/ai career_ops/ingestion career_ops/evals tests/test_ai_prompts.py tests/test_pydantic_ai_service.py tests/test_deterministic_ai_service.py
git commit -m "refactor: extract typed AI prompt boundary"
```

---

### Task 4: Factory-Backed Pipelines, Explicit Metadata, and Mock Integration

**Files:**
- Create: `tests/test_mock_integration.py`
- Modify: `career_ops/automation/gmail_ingestion.py`
- Modify: `career_ops/ingestion/job_ingestion.py`
- Modify: `career_ops/models/__init__.py`
- Modify: `career_ops/gmail/sync.py`
- Modify: `career_ops/gmail/single_message.py`
- Modify: `career_ops/showcase/runner.py`
- Modify: `tests/test_gmail_ingestion.py`
- Modify: `tests/test_gmail_sync.py`
- Modify: `tests/test_job_ingestion.py`
- Modify: `tests/test_showcase.py`

**Interfaces:**
- Consumes: `build_ai_service() -> CareerAIService` from Task 2.
- Produces: `EmailClassification.model_name: str` and `fallback_status: str`.
- Produces: default pipelines that honor `CAREER_FORGE_MODE`.

- [ ] **Step 1: Write the provider-metadata regression test**

Construct `GmailSyncService` with a `GmailIngestionPipeline` using
`DeterministicAIService` (a valid protocol implementation with no concrete
`.model` attribute), process one interview email, and assert the classified
event:

```python
classified = next(
    event for event in event_log.read_all()
    if event.event_type == EventType.GMAIL_MESSAGE_CLASSIFIED
)
assert classified.data["model_name"] == "deterministic:rules-v1"
assert classified.data["fallback_status"] == "deterministic"
```

The existing code must fail because Gmail sync reaches for the absent concrete
`.model` assumption instead of using typed plan metadata.

- [ ] **Step 2: Run the regression test to verify failure**

Run: `python -m pytest tests/test_gmail_sync.py -q`

Expected: FAIL on provider metadata or concrete service attribute access.

- [ ] **Step 3: Carry metadata through the domain plan**

Add to `EmailClassification`:

```python
model_name: str = "unknown"
fallback_status: str = "none"
```

Populate both fields from `PydanticAIEmailEvaluation` in
`GmailIngestionPipeline.classify`. Update Gmail sync and single-message event
payloads to use `plan.classification.model_name` and
`plan.classification.fallback_status`.

- [ ] **Step 4: Replace concrete default construction with the factory**

In both pipelines, use `build_ai_service()` only when the narrow dependency is
absent. Preserve the review fix that fully injected showcase dependencies do
not read settings. Keep job-fetch timeout construction independent from AI
provider selection.

- [ ] **Step 5: Make the public showcase explicitly mock-backed**

Update `ShowcaseRunner` to accept `CareerAIService | None`, default to
`MockAIService`, and report `mode="mock"`. Preserve its fixed Gmail and ATS
inputs, three scenario outputs, no-network behavior, and no-write guarantee.

- [ ] **Step 6: Write the full mock-boundary integration test**

In `tests/test_mock_integration.py`, define typed fake Gmail and Notion adapters,
run a Gmail interview message through `GmailSyncService`, run a static Lever URL
through `WorkflowOrchestrator`, and assert:

- the mock AI classification and fit evaluation were used;
- Notion mutations were planned and applied through the fake gateway;
- the Gmail message was acknowledged only after successful execution;
- model and fallback metadata appear in append-only events; and
- no environment credentials or network client is required.

- [ ] **Step 7: Run focused integration and showcase tests**

```bash
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv uv run pytest \
  tests/test_gmail_ingestion.py tests/test_gmail_sync.py \
  tests/test_job_ingestion.py tests/test_mock_integration.py tests/test_showcase.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add career_ops/automation career_ops/ingestion career_ops/models career_ops/gmail career_ops/showcase tests
git commit -m "refactor: route workflows through configured AI services"
```

---

### Task 5: Exact 20-Prompt Benchmark Contract

**Files:**
- Modify: `benchmark/bench.py`
- Modify: `benchmark/results.json`
- Modify: `tests/test_benchmark.py`

**Interfaces:**
- Consumes: `CareerAIService` and `MockAIService` from Task 2.
- Produces: `BenchmarkReport(n, median_ms, p95_ms, throughput_per_min, success_rate, details)`.
- Produces: `BenchmarkDetail(prompt_id, latency_ms, success, error)`.

- [ ] **Step 1: Replace schema assertions with the required contract**

```python
payload = json.loads(output.read_text())
assert set(payload) == {
    "n",
    "median_ms",
    "p95_ms",
    "throughput_per_min",
    "success_rate",
    "details",
}
assert payload["n"] == 1
assert set(payload["details"][0]) == {
    "prompt_id",
    "latency_ms",
    "success",
    "error",
}
```

Keep tests proving exactly 20 unique non-empty prompts, nearest-rank p95,
expectation validation outside timing, and prompt participation in input.

- [ ] **Step 2: Run benchmark tests to verify schema failure**

Run: `python -m pytest tests/test_benchmark.py -q`

Expected: FAIL because the current report uses `total_cases`,
`median_latency_ms`, `throughput_per_second`, and `results`.

- [ ] **Step 3: Implement the exact report models**

```python
class BenchmarkDetail(BaseModel):
    model_config = ConfigDict(frozen=True)
    prompt_id: str
    latency_ms: float
    success: bool
    error: str | None = None


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    n: int
    median_ms: float
    p95_ms: float
    throughput_per_min: float
    success_rate: float
    details: list[BenchmarkDetail]
```

Calculate `throughput_per_min` as `n / total_seconds * 60`. Type
`run_benchmark(..., service: CareerAIService, ...)` and use `MockAIService` in
`main()`.

- [ ] **Step 4: Update human output and CLI exit behavior**

Print n, success rate, median, p95, and prompts/minute. Exit 0 only when all
details succeed. Keep `--output` and the default 20-prompt fixture path.

- [ ] **Step 5: Run and persist the benchmark**

```bash
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv uv run pytest tests/test_benchmark.py -q
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv uv run python benchmark/bench.py --output benchmark/results.json
jq -e '.n == 20 and .success_rate == 1 and (.details | length == 20)' benchmark/results.json
```

Expected: tests pass, benchmark exits 0, and jq exits 0.

- [ ] **Step 6: Commit**

```bash
git add benchmark tests/test_benchmark.py
git commit -m "feat: publish required benchmark metrics schema"
```

---

### Task 6: CI Matrix, Docker Mock Mode, Documentation, and Release Metadata

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `Dockerfile`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ARCHITECTURE.md`
- Modify: `PROJECT_STATE.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/EVALS.md`
- Modify: `docs/PYDANTIC_AI.md`
- Modify: `docs/RELEASE_CHECKLIST.md`
- Modify: `career_ops/__init__.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: all runtime, compatibility, and benchmark contracts from Tasks 1-5.
- Produces: CI coverage for Python 3.10-3.12 and explicit secret-free mock mode.
- Produces: documented 0.6.0 release contract.

- [ ] **Step 1: Rewrite CI as test matrix plus quality job**

The test job must use:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
env:
  CAREER_FORGE_MODE: mock
steps:
  - uses: actions/checkout@v7
  - uses: actions/setup-python@v7
    with:
      python-version: ${{ matrix.python-version }}
      cache: pip
  - run: python -m pip install -r requirements-dev.txt
  - run: python -m pytest -q --cov --cov-report=term-missing --cov-report=xml
```

Add a Python 3.12 `quality` job that installs the same requirements and runs:

```bash
ruff check .
ruff format --check .
pyright
python benchmark/bench.py --output benchmark-results.json
./demo.sh --json
docker build -t career-forge-demo .
docker run --rm -e CAREER_FORGE_MODE=mock career-forge-demo ./demo.sh --json
```

Upload `benchmark-results.json` as an artifact. Make `quality` depend on the
matrix test job.

- [ ] **Step 2: Make Docker mode explicit**

Add `CAREER_FORGE_MODE=mock` to the Docker environment. Preserve Python 3.12,
the `uv.lock` install, non-root user, and existing command.

- [ ] **Step 3: Update environment documentation**

Place this block at the top of `.env.example`:

```dotenv
# mock: deterministic, credential-free, and safe for demo/CI
# real: configured Pydantic AI provider; requires the provider credentials below
CAREER_FORGE_MODE=mock
```

Retain every existing live-provider variable.

- [ ] **Step 4: Synchronize public documentation**

Update README and architecture docs with:

- Python 3.10-3.12 support;
- mock/real mode commands;
- factory and prompt-codec boundaries;
- exact benchmark field names and fresh measured values;
- CI's secret-free contract;
- secure real-mode credentials through environment variables or encrypted
  GitHub secrets, guarded from default CI execution.

Do not rename the repository or alter the established product tagline.

- [ ] **Step 5: Publish release metadata**

Set `pyproject.toml` and `career_ops.__version__` to `0.6.0`, add a dated 0.6.0
changelog entry, mark the hardening phase complete in `ROADMAP.md` and
`PROJECT_STATE.md`, then refresh `uv.lock`.

- [ ] **Step 6: Run documentation and metadata checks**

```bash
rg -n "CAREER_FORGE_MODE|Python 3.10|throughput_per_min" README.md ARCHITECTURE.md docs .env.example
UV_CACHE_DIR=/tmp/careerforge-uv uv lock --check
UV_CACHE_DIR=/tmp/careerforge-uv uv run python -c "import career_ops; assert career_ops.__version__ == '0.6.0'"
```

Expected: all new contracts are documented and version assertion passes.

- [ ] **Step 7: Commit**

```bash
git add .github Dockerfile .env.example README.md AGENTS.md ARCHITECTURE.md PROJECT_STATE.md ROADMAP.md CHANGELOG.md docs career_ops/__init__.py pyproject.toml uv.lock
git commit -m "docs: release CareerForge 0.6.0 mock-mode showcase"
```

---

### Task 7: Full Verification, Review, and Pull Request

**Files:**
- Review: every file changed since `main`.
- Create remotely: focused pull request from `codex/mock-mode-hardening-0.6.0`.

**Interfaces:**
- Consumes: the complete 0.6.0 implementation.
- Produces: locally verified branch, green GitHub Actions, resolved review feedback, and PR URL.

- [ ] **Step 1: Run format and static analysis**

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv run ruff format .
UV_CACHE_DIR=/tmp/careerforge-uv uv run ruff check .
UV_CACHE_DIR=/tmp/careerforge-uv uv run ruff format --check .
UV_CACHE_DIR=/tmp/careerforge-uv uv run pyright
```

Expected: no changes after the format pass, no lint errors, and zero Pyright
errors.

- [ ] **Step 2: Run the full test suite with coverage**

```bash
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv uv run \
  pytest -q --maxfail=1 --cov --cov-report=term-missing --cov-report=xml
```

Expected: all tests pass and coverage is at least 80 percent.

- [ ] **Step 3: Verify all supported Python versions**

```bash
for version in 3.10 3.11 3.12; do
  CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv \
    uv run --python "$version" pytest -q --maxfail=1
done
```

Expected: all three runs pass.

- [ ] **Step 4: Verify demo and benchmark behavior**

```bash
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv ./demo.sh --json
CAREER_FORGE_MODE=mock UV_CACHE_DIR=/tmp/careerforge-uv \
  uv run python benchmark/bench.py --output results.json
jq -e '.n == 20 and .success_rate == 1 and (.details | length == 20)' results.json
```

Expected: demo exits 0, benchmark exits 0, and schema assertion passes.

- [ ] **Step 5: Verify package builds**

```bash
UV_CACHE_DIR=/tmp/careerforge-uv uv build
python -m pip install -r requirements-dev.txt
```

Expected: wheel and sdist are version 0.6.0 and pip installation succeeds.

- [ ] **Step 6: Verify Docker when available**

```bash
docker build -t career-forge-demo .
docker run --rm -e CAREER_FORGE_MODE=mock career-forge-demo ./demo.sh --json
```

Expected: both commands exit 0. If Docker is unavailable locally, record the
exact error and require these steps to pass in GitHub Actions before completion.

- [ ] **Step 7: Review the final diff**

Run:

```bash
git diff main...HEAD --check
git diff main...HEAD --stat
git status --short
```

Inspect every changed file for unnecessary wrappers, untyped dictionaries,
hidden settings reads, stale names, secret exposure, and documentation drift.
Run a secret-pattern scan excluding generated lock and binary assets.

- [ ] **Step 8: Commit verification-only fixes**

If verification changed formatting, generated results, or documentation, stage
only those focused files and commit:

```bash
git commit -m "test: finalize mock-mode showcase verification"
```

Do not create an empty commit.

- [ ] **Step 9: Push and open the pull request**

Push `codex/mock-mode-hardening-0.6.0` and open a PR to `main` summarizing
runtime architecture, compatibility, tests, benchmark schema, and exact local
verification evidence.

- [ ] **Step 10: Require green CI and resolve review feedback**

Wait for every Python matrix job, quality job, benchmark artifact, Docker build,
and Docker smoke test. Read all review threads. Apply technically valid feedback
with regression tests, re-run focused local checks, push a follow-up commit, and
resolve threads only after fixes are present. Do not merge without an explicit
integration choice from the repository owner.
