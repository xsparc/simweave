# SW028 validation

Focused acceptance on 2026-11-02 passed 24 bundle tests. Every test forbids
simulation execution. Coverage includes deterministic export, existing v2 renderer
identity, the retained two-source example, malformed UTF-8, excessive input,
duplicate JSON keys, deep nesting, unknown fields, unsupported/noninteger versions,
changed source/report/direction, over-budget plans, nested mutation, exact HTML/CSV
bytes, exclusive output, unchanged sources and fixed error diagnostics.

The existing HTML renderer and styling are unchanged. Its earlier desktop/mobile
layout evidence remains in portable-plan-review-validation.md; this slice adds
no browser-layout certification. A bundle proves local consistency only and
retains normalized data rather than original source-file byte formatting.


Final regression: 447 passed, ten skipped (nine PostgreSQL tests without a fixture
DSN and one host symlink test). Installed MuJoCo checks passed. Ruff lint/format,
static governance and strict governance dated 2026-11-02 passed. Isolated wheel
and source distribution builds passed. The existing Starlette/httpx deprecation
warning remains. No live PostgreSQL, ROS/Gazebo or new browser session was run
for this pure evidence-contract slice; remote CI results are separate.

The installed wheel also passed export, offline verification and HTML rendering
against the retained synthetic before/after plans. Existing renderer bytes match
source-based rendering in the acceptance tests.
