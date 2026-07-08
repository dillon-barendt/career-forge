# Release Checklist

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Run `uv lock`.
4. Run `uv run ruff check .`.
5. Run `uv run pytest`.
6. Verify docs links and examples use fake data only.
7. Confirm `.env.example` has no real secrets.
8. Tag release after CI passes.
