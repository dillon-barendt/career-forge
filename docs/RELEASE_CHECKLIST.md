# Release Checklist

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Confirm `pyproject.toml`, `career_ops.__version__`, and `uv.lock` use the
   same release version.
4. Run `UV_CACHE_DIR=/tmp/careerforge-uv uv lock --check`.
5. Run `scripts/dev_check.sh` in `CAREER_FORGE_MODE=mock` on a supported Python
   version (3.10–3.12).
6. Build and smoke-run the non-root demo image explicitly in mock mode:

   ```bash
   docker build -t career-forge-demo .
   docker run --rm -e CAREER_FORGE_MODE=mock career-forge-demo ./demo.sh --json
   ```

7. Verify the GitHub Actions test matrix covers Python 3.10, 3.11, and 3.12 and
   that the dependent quality job uploads `benchmark-results.json`.
8. Confirm default CI sets `CAREER_FORGE_MODE=mock` and has no provider secrets.
   Any real-mode job must use encrypted GitHub secrets and remain guarded from
   pull requests and default CI execution.
9. Verify docs links and examples use fake data only.
10. Confirm `.env.example` has no real secrets.
11. Confirm the documented benchmark metrics match `benchmark/results.json`.
12. Tag release after CI passes.
