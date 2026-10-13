# SW006 evidence workflow validation

Validation date: 2026-10-14. Acceptance is defined by ADR 0004.
Implementation and verification are recorded separately from usability targets.

## Executed checks

Targeted evidence and regression checks passed: 53 tests. They exercise real
reference/MuJoCo recordings, corruption with recomputed checksums, preview fidelity,
unknown/traversal members, duplicates, symlinks, size limits, runtime mismatch
before execution, fixed container controls/cleanup, and hostile HTML names/CSP.

The final portable suite passed 129 tests on Python 3.12.13, including the added
central-directory preflight and overwrite checks. Ruff lint/format, JavaScript
syntax, static/dated strict governance, source/wheel builds, and wheel contents
passed. The existing Starlette/httpx TestClient deprecation warning remains.

All 16 live ROS/Gazebo conformance checks passed in the new image. The local
ten-seed reference/MuJoCo positive and degraded matrices verified all 80 recordings
and both evidence bundles, preserving exits 0 and 1 respectively. CI additionally
runs the ten-seed MuJoCo/Gazebo matrix and checks the public container-rerun CLI.

`scripts/check_evidence_ci.py` passed against the local ROS/Gazebo image. The
original and fresh container each executed six runs: baseline/degraded controller
on reference, MuJoCo, and Gazebo at seed 42. All telemetry digests and full results
matched, with both suite exit codes equal to 1 and reproduction exit 0. Both
bundles passed integrity verification. The runtime was Linux x86_64, Python 3.12.3,
MuJoCo 3.15.0, ROS Jazzy/Gazebo Harmonic; source revision `5705a96` and installed
implementation digest `ababbb9d8f6bd2f42a7a71f07df72e0e31e0e8a7c948a999b560d96d77300fc0`.
Docker reported local image ID
`sha256:6022c5b87dd24bbfe53eed351e389583b7714c6d85045585c5b169b4cb0f630c`.
The retained-image check used the actual installed ID, not an inferred registry
or configuration digest. ROS emitted its existing localhost-only deprecation warning.

Browser review used a loopback static HTTP preview, without an API or simulator.
Three controlled workflows identified failures for reference seeds 7 and 42 and
MuJoCo seed 7. Export preparation took 1.026, 0.834, and 0.565 seconds respectively;
these are automation observations, not human task-completion estimates. The
selected seeds, adapters, failed gates, and JSON contents were checked in the UI.
Browser error/warning logs were empty.
The actual downloaded JSON was parsed and validated against the suite/comparison
contracts. Hostile closing-script/image/event-handler text rendered as text, with
zero injected images or dialogs. See [offline review screenshot](../assets/offline-evidence.jpg).

## Remaining acceptance gaps

The browser tool rejects file-protocol navigation. Direct double-click/file-open
verification is unexecuted; the generated document embeds its data, script, and
CSS, and the static preview exercised those same bytes. The first actual JSON
download completed, but the tool stalled for roughly six hours; therefore the
two-minute end-to-end identify-and-save target is not established. Subsequent
walkthroughs verified the visible copyable JSON without repeating the dialog.
SW006 remains in progress in the evidence index for these validation gaps.

Image retention is operator-managed. Bundles do not contain a container image or
source code and cannot authenticate operator-supplied provenance. No image was
published. Same-image rerun evidence applies to the tested runtime and host;
different machines can still produce numerical differences, which are reported.
