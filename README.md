# SimWeave

Vendor-neutral simulation experiments for robotics and physical AI.

Define a world, robot, controller, sensor noise, disturbances, seed, and quality
gates in one JSON scenario. Run it headlessly, inspect telemetry, and verify the
recording. The first experiment is a one-dimensional cart recovering from a force
disturbance.

## Local CLI

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -e '.[dev]'
simweave validate examples/cart-recovery.json
simweave run examples/cart-recovery.json --output .simweave/example
simweave replay .simweave/example
```

Output contains `scenario.json`, `result.json`, and streaming `telemetry.jsonl`.
Exit codes: 0 = gates pass, 1 = completed with failed gates, 2 = input/runtime error.
Existing output directories are never overwritten. `simweave init scenario.json`
creates a default scenario; `simweave schema` prints its JSON Schema.

The reference simulator is a small deterministic test/demo model. Repeatability
requires the same engine, adapter, dependency versions, platform, and seed;
different simulators are not expected to be numerically identical.

## Engineering

```sh
python -m pytest
ruff check .
ruff format --check .
python scripts/check_governance.py --strict
```

See [architecture](docs/architecture/overview.md), [three-PR roadmap](docs/roadmap/implementation-roadmap.md),
[security boundary](docs/security/threat-model.md), and [validation](docs/governance/verification-and-validation.md).
`uv.lock` records the resolved environment; use `uv sync --frozen --extra dev`
for a locked development install.

Licensed under the MIT License.
