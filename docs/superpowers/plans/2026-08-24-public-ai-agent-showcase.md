# Public AI Agent Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a credential-free CareerForge demo, a reproducible 20-case benchmark, and CI/documentation that make the repository portfolio-ready.

**Architecture:** Extract deterministic reasoning into an injectable AI service, then route the showcase and benchmark through the existing typed Gmail, job-ingestion, and material-generation paths. Preserve Pydantic AI as the live adapter and use Docker plus CI to prove the offline path.

**Tech Stack:** Python 3.12, Pydantic v2, Typer/Rich, pytest, Ruff, Pyright, Docker, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-24-public-ai-agent-showcase-design.md`

## Global Constraints

- Preserve the name `career-forge` and use the public display name `CareerForge`.
- Use the tagline “CareerForge — AI agents that forge career data into action.”
- Demo and benchmark must run without credentials or network access.
- Preserve dry-run defaults and existing external-side-effect safety.
- Use Python 3.12 and Pydantic v2 APIs.
- Keep all existing 70 tests passing.

---

### Task 1: First-class deterministic AI boundary

**Files:**
- Create: `career_ops/ai/contracts.py`
- Create: `career_ops/ai/deterministic.py`
- Modify: `career_ops/ai/pydantic_ai_service.py`
- Modify: `career_ops/automation/gmail_ingestion.py`
- Test: `tests/test_deterministic_ai_service.py`

**Interfaces:**
- Produces: `EmailClassificationService.classify_email(message) -> PydanticAIEmailEvaluation`.
- Produces: `OpportunityEvaluationService.evaluate(posting) -> OpportunityEvaluation`.
- Produces: `DeterministicAIService` implementing both protocols.
- Consumes: existing Pydantic models and scoring rules.

- [ ] Write tests proving deterministic classifications and opportunity evaluations match current fallback behavior.
- [ ] Run `pytest tests/test_deterministic_ai_service.py -q` and confirm import/behavior failures.
- [ ] Implement protocols and deterministic service; delegate Pydantic AI fallback to it.
- [ ] Type the Gmail pipeline against the protocol instead of the concrete live service.
- [ ] Run focused tests and the existing Pydantic AI/Gmail suites.
- [ ] Commit the slice.

### Task 2: Typed showcase runner and demo entrypoint

**Files:**
- Create: `career_ops/showcase/__init__.py`
- Create: `career_ops/showcase/runner.py`
- Create: `career_ops/showcase/demo.py`
- Create: `demo.sh`
- Test: `tests/test_showcase.py`

**Interfaces:**
- Produces: `ShowcaseRunner.run() -> ShowcaseReport` with three typed `ShowcaseScenario` results.
- Produces: `render_human(report) -> str` and JSON via `model_dump_json()`.
- Consumes: deterministic service, Gmail pipeline, job pipeline, and resume material builder.

- [ ] Write tests proving the three scenarios exercise classification, extraction/scoring, and material generation.
- [ ] Run focused tests and confirm the missing showcase module fails.
- [ ] Implement fixed fake fixtures and the runner with explicit dependency injection.
- [ ] Implement `python -m career_ops.showcase.demo [--json]` and `demo.sh`.
- [ ] Run focused tests, `./demo.sh`, and the JSON smoke command.
- [ ] Commit the slice.

### Task 3: Measured 20-case benchmark

**Files:**
- Create: `benchmark/__init__.py`
- Create: `benchmark/prompts.json`
- Create: `benchmark/bench.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces: `run_benchmark(cases, service, clock) -> BenchmarkReport`.
- Produces: `nearest_rank_p95(latencies_ms: list[float]) -> float`.
- Consumes: the deterministic AI service and typed fixture models.

- [ ] Write tests with literal timings proving median, nearest-rank p95, throughput, success rate, and JSON persistence.
- [ ] Run focused tests and confirm the missing benchmark module fails.
- [ ] Implement the two case types and observable validators with no external calls.
- [ ] Add exactly 20 representative fixed cases.
- [ ] Run the benchmark and focused tests; confirm JSON and human output.
- [ ] Commit the slice.

### Task 4: Reproducible container and CI proof

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Modify: `scripts/dev_check.sh`
- Modify: `uv.lock`

**Interfaces:**
- Produces: `docker run --rm career-forge-demo` executing `demo.sh`.
- Produces: one CI job that proves lint, formatting, typing, tests, smoke demo, benchmark, and Docker.

- [ ] Add development dependencies for Pyright and coverage; regenerate the lockfile.
- [ ] Fix only lint/type issues surfaced by the strengthened checks.
- [ ] Add Docker build and default command with a non-root runtime user.
- [ ] Extend local and CI verification commands.
- [ ] Run Ruff, Pyright, pytest with coverage, demo, benchmark, Docker build, and Docker run.
- [ ] Commit the slice.

### Task 5: Public README, demo GIF, and synchronized docs

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ARCHITECTURE.md`
- Modify: `ROADMAP.md`
- Modify: `DATA_MODEL.md`
- Modify: `AUTOMATIONS.md`
- Modify: `.env.example`
- Modify: `CONTRIBUTING.md`
- Modify: `CODE_OF_CONDUCT.md`
- Modify: `CHANGELOG.md`
- Create: `docs/assets/career-forge-demo.gif`
- Create: `scripts/render_demo_gif.py`

**Interfaces:**
- Produces: a README landing section with badges, tagline, GIF, three commands, three prompt/output examples, benchmark results, and architecture links.
- Consumes: verified demo and benchmark output only; no invented metrics.

- [ ] Generate the GIF from fake demo output and verify its frame count/duration.
- [ ] Rewrite the README landing section while retaining operator and integration reference material.
- [ ] Synchronize architecture, agent, roadmap, data-model, automation, environment, contribution, conduct, and changelog documentation.
- [ ] Run link/reference checks plus the complete verification suite.
- [ ] Review the final diff for stale naming, placeholders, secrets, and unnecessary complexity.
- [ ] Commit and publish the focused branch for review.

