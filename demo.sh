#!/usr/bin/env bash
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  exec uv run python -m career_ops.showcase.demo "$@"
fi

exec python -m career_ops.showcase.demo "$@"
