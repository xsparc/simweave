# Contributing

Read the architecture, roadmap, and project AGENTS.md before changing behavior.
Use Python 3.11+ and `uv sync --frozen --extra dev --extra mujoco`, or an isolated
virtual environment with `pip install -e '.[dev,mujoco]'`.

Run pytest, Ruff lint/format, and the strict governance checker. Add regression
tests for changed contracts, security boundaries, and concurrency behavior. New
simulators need reset, stepping, deterministic envelope, and cleanup tests using
the real simulator; mark unavailable integration checks explicitly.

Use small pull requests with the problem, resulting behavior, validation, and
remaining gaps. Keep compatibility changes explicit. Never commit tokens, run
databases, local paths, logs from private environments, or generated recordings.
Code and documentation contributed here are licensed under MIT.

After an intentional dependency update, regenerate the container dependency export:

```sh
uv export --frozen --no-dev --extra mujoco --no-emit-project --no-header --format requirements-txt --output-file requirements.lock
```

Commit `uv.lock` and `requirements.lock` together and rerun the real MuJoCo and
container checks. The core CI matrix uses the frozen lockfile.
