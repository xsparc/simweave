# Team evidence validation

Date: 2026-10-14. Baseline: `401c0f3cc8fd97530aa503601e0c7cc1fcb11533`.

SW008 adds archive recovery and catalog API authorization, with no simulator,
numerical inference or browser behavior changes. The following checks were observed
locally before draft PR delivery; hosted CI is reported separately in the PR.

- Windows created 100 distinct reference controller snapshots (two seeds and two
  roles each, 20 steps), three approval events including rollback, and 100 pinned
  comparisons. These deliberately small populations produce inconclusive statistics;
  they exercise storage portability, not calibrated statistical conclusions.
- Windows export/restore/re-export and Linux container restore/re-export preserved
  identical archive bytes, including every approval/comparison digest. Stream hash:
  `3b7f357b0039edf13a0b1521412a3a56e07ee7e6991e0c3e627eeb3952d57346`.
- All 190 portable tests passed, including 27 new tests: archive round-trip/no overwrite/immutable restored
  history, corruption/truncation/trailing bytes/duplicate/order/generation/reference/
  rollback policy/timestamp rejection, size limits, tenant roles, forged identity,
  concurrent approvals, restart, pagination, uploads and configuration validation.
  Tests also cover overlapping labels in both tenants, every role's read access,
  binary OpenAPI input, bounded numeric SQL cursors, and Windows device-name tenants.
- The standard-library client completed show/import/promote/read-back against a
  temporary live loopback API with separately generated role credentials. The
  server-derived approval subject was verified. The test server was stopped.
- Ruff lint/format, whitespace checks and dated strict governance passed. Source
  and wheel builds succeeded. The final installed wheel restored/re-exported the
  100-build archive on Windows and Linux; Linux also provisioned the catalog API
  and checked its OpenAPI binary upload contract. Wheel SHA-256:
  `bb5c6599e3b0f4c3905c1407221bc1ee6f48415755ce91b15b30cbeaaf5a216c`.
  The isolated Linux container had no network or host mounts; the final wheel was
  installed over the previously built dependency image without fetching packages.
- CI now carries a Windows-created 100-build archive into an Ubuntu restore job.
  Existing three-OS/Python, MuJoCo, container and native Gazebo jobs remain enabled.
  Local tests included installed MuJoCo; no new live Gazebo runs were needed for
  these persistence/authorization changes. The existing Starlette/httpx deprecation
  warning remains; it is not a test failure.

Limits: no external identity provider, remote deployment, signed provenance,
network filesystem, load benchmark or new live ROS execution is claimed. Archive
checksums and static bearer principals are not cryptographic proof of human approval.
Restore preserves historical decisions rather than recomputing them on a new runtime.
Prior SW005/SW006 browser gaps remain unchanged.
