#!/usr/bin/env bash
set -euo pipefail

uv sync --extra dev
cp -n .env.example .env
uv run pre-commit install
