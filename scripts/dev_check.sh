#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest --cov --cov-report=term-missing
./demo.sh --json
uv run python benchmark/bench.py --output benchmark-results.json
