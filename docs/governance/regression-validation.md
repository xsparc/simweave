# SW005 regression workflow validation

Approved scope: scenario/seed regression suites and comparison dashboard under
ADR 0003. This record distinguishes local portable tests, real simulator runs,
browser workflow checks, and hosted CI.

## Executed on 2026-10-13

- Windows Python 3.12.13: 109 portable tests passed. Coverage includes invalid
  matrices, bounds, duplicate seeds, controller expansion, mismatched comparison
  inputs, corrupt reports/recordings, unavailable backends, execution errors,
  tenant isolation, request limits, API comparison, CLI exit codes, and replay.
- Real local MuJoCo 3.15.0/reference: 40 positive-control runs and 40 degraded
  runs. All 80 full recordings verified; CLI exit codes 0/1 matched expectations.
- Real ROS 2 Jazzy/Gazebo Harmonic and MuJoCo in the Linux integration image:
  40 positive and 40 degraded runs, each matrix covering two controllers, ten
  seeds, and both native engines. All 80 recordings verified and JSON/JUnit
  reports were produced. No unavailable-engine skips.
- All 15 original live ROS/Gazebo conformance tests passed again after the
  discovery repair in 136.50 seconds. A new lost-response test passed separately
  with the real ROS executor and native fixture (16 live checks total). Containers
  ran unprivileged, without external networking, capped at two CPUs/4 GiB.
- Ruff lint/format, both JavaScript syntax checks, static and dated strict
  governance checks, and source/wheel packaging passed.
- A real browser compared completed reference runs, displayed both trajectories
  and four metric deltas, focused the newly failing gate, and downloaded a JSON
  comparison. The downloaded file validated against the comparison contract.
  The browser also opened the real 20-pair MuJoCo/Gazebo suite report, selected
  a Gazebo pair, navigated to the next failing pair and gate, and displayed the
  quality and regression failures. No browser console errors were captured.
  Screenshot: `docs/assets/regression-comparison.jpg`.

The original two-minute end-to-end walkthrough target remains unverified: browser
automation waited unusually long around native upload/download dialogs. Functional
inspection and export succeeded; that elapsed time is not a valid performance or
usability benchmark. No broad user study or responsive-device matrix was run.
This draft retains the timing follow-up rather than claiming the target passed.

The live image uses the SW004 runtime: Ubuntu 24.04, Python 3.12.3, Gazebo Sim
8.15.0/DART, ROS 2 Jazzy, and MuJoCo 3.15.0. Its base digest and Python lock are
pinned; apt package resolution is not a hermetic environment lock. Tests emitted
the existing Starlette/httpx deprecation warning, and ROS emitted its existing
localhost-discovery deprecation warning.

CI now requires the two-engine ten-seed positive/negative checks and retains all
reports and recordings for seven days. Hosted CI outcomes are recorded in the PR;
local evidence above does not imply an unexecuted CI check passed.

Initial hosted CI exposed one timeout on the first read-only feature-discovery
RPC. The other hosted run passed conformance and the complete native matrix.
The transport now retries only that read within its original deadline. New
fault-injection tests exercise lost responses, bounded retries, and the invariant
that mutation timeouts never retry. This is consistent with the discovery race
reported in [ROS middleware issue 842](https://github.com/ros2/rmw_fastrtps/issues/842)
(opened 2025-08-12); the CI log alone does not establish its precise middleware
cause. Artifact collection now skips stages that never launched a container.

Known boundaries: sequential local suite scheduling; single-host service;
built-in cart only; 101-point plot previews; unsigned imported summaries;
no statistical-significance claim. A timed browser walkthrough is not a broad
usability study. Reproducible environment bundles and worker routing are deferred.
