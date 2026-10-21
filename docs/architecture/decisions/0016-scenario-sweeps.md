# ADR 0016: deterministic scenario sweep planning

Status: accepted

Date: 2026-10-21

SW018 follows retained-evidence integrity under delegated next-scope selection.
Add a pure version-1 Sweep contract and plan function that produces the existing
Suite contract. Accept one base scenario and 1..3 explicit axes drawn from robot
mass, damping, initial position, initial velocity and sensor position noise. Each
axis has 1..8 unique finite values; duplicate fields and more than eight Cartesian
combinations fail. Preserve input axis/value order, with the last axis varying
fastest. Names append a stable sweep index within the existing 100-character cap.

Revalidate each generated Scenario and the complete Suite before output. Existing
adapter, seed, controller, regression-gate, 64-run and 200000-step checks apply.
Planning revalidates model data to reject mutated nested inputs. The CLI accepts
at most 64 KiB, emits compact Suite JSON to stdout or an exclusive new file, and
rejects output exceeding the existing 64 KiB suite-input limit.

Acceptance: stable expansion/digests, preserved base input, strict field/value and
matrix bounds, invalid requests create no output, existing files are preserved,
schema emission and real reference/MuJoCo suite execution where installed.

This is plan-only authoring. It adds no solver, adaptive tuning, arbitrary field
paths, execution endpoint, automatic baseline promotion or statistical correction.
Generated suites use the existing execution and evidence pipeline. Explicit
parameter grids are not coverage or physical validity guarantees.
