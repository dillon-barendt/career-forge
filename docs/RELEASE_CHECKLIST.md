# Release Checklist

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Run `uv lock`.
4. Run `scripts/dev_check.sh`.
5. Build and smoke-run `career-forge-demo` with Docker.
6. Verify docs links and examples use fake data only.
7. Confirm `.env.example` has no real secrets.
8. Confirm the committed benchmark metrics match `benchmark/results.json`.
9. Tag release after CI passes.
