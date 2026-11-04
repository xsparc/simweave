# SW028 verification and handoff

Validated 2026-11-04 at merged main 307616fe4ea392e995e037db396df0b32b2bfdca.
The three saved SW028 tasks were implemented in PR #33 before this iteration.
This delivery verifies and preserves that implementation; it introduces no new
runtime behavior and does not repeat or replace those completed features.

- Full suite: 447 passed, ten skipped (nine PostgreSQL tests without a DSN and
  one existing host symlink test). MuJoCo coverage passed.
- Ruff lint and format checks passed.
- Existing bundle acceptance covers canonical export/read/verify/render, duplicate
  fields, tampering, reversed direction, source identities, exclusive output and
  no simulator execution.
- Chromium rendered a decoded retained bundle at 1280x900 and 390x900: no page
  overflow, no scripts or page errors, and two contained tables.

Existing Starlette/httpx deprecation remains. No native ROS/Gazebo, PostgreSQL
service or new physics-equivalence claim is included. The shared next-five
handoff now distinguishes completed work from planned TC022/SW029 tasks.

Project-specific static and 2026-11-04 strict governance checks passed.
Offline source/wheel builds passed; archive inspection found no private state.
The plugin self-checker was also attempted; it requires project identity
opensteward-control-plane and its own registry dialect, so it rejects these
independent project registries. The repository-specific gate is applicable here;
no project identity or historic registry was rewritten to satisfy that self-check.
