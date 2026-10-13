# ADR 0004: Portable evidence and explicit container reruns

Status: accepted

Date: 2026-10-14

SW006 implements the maintainer-approved failure bundles and offline reports,
starting from squash-merged main `2173cd68aac61930e6f36e229e71762951f894c3`.

## Decision

Every completed suite writes a standalone HTML review and a versioned ZIP bundle,
including passing suites and suites with execution errors. The bundle contains
only fixed JSON/JSONL members: the validated suite report, complete recordings,
and a SHA-256 manifest. A bounded reader checks the entire archive and verifies
recordings without extracting filenames or executing bundled content. Partial
recordings from execution errors stay in the original suite directory.

Capture Python, OS family, architecture, a fixed list of relevant dependency
versions, and a digest of installed SimWeave Python source. Optional explicit
source revision and container image ID are operator assertions, not attestations.
Do not inventory host identity, arbitrary installed packages, or environment
variables. An exact container image ID captures its native dependencies; images
must be retained separately. Missing provenance remains visible as unknown.

`rerun` requires an operator-selected local Docker image ID that matches the
recorded image ID. Never pull an image or select one solely from bundle input.
Run the installed fixed CLI in a fresh, unprivileged, network-disabled container
with resource limits, no host mounts, and no Docker socket. Check the installed
code/runtime fingerprint before simulation. Compare complete telemetry digests
and execution outcomes afterwards; matching fingerprints do not guarantee
cross-machine bitwise equality. Save fresh reports and a reproduction verdict.

The offline report embeds bounded validated previews and precomputed comparisons,
with a restrictive hash-based CSP and escaped data. It needs no API, external
assets, or simulator. Show failures first, support keyboard navigation, metric
and gate inspection, and a selected-pair JSON export with a visible text fallback.
The report is unsigned review evidence; full bundle validation remains a CLI task.

## Acceptance and verification

- Capture inputs, seeds, revision when supplied, runtime/dependency fingerprints,
  and image identity when supplied; clearly label unknown provenance.
- Verify ZIP member sets, sizes, hashes, recording integrity, and preview fidelity;
  reject traversal, duplicates, symlinks, extra files, and excess decompression.
- One command reruns a retained compatible image; mismatch prevents execution.
  Real reference, MuJoCo, and Gazebo reruns preserve known failure outcomes.
- Open the HTML without an API or simulator. In three observed walkthroughs,
  identify and export a known failure within two minutes. Separate controlled
  workflow timings from human usability research.
- Include HTML and bundles in CI artifacts; verify packaging and all existing
  checks. Trace implementation, tests, risks, and actual gaps in governance.

Expected paths: evidence/runtime/container modules, CLI/suite integration, static
offline assets, targeted tests, CI, and operations/governance documentation.
No hosted artifact storage, image publication, remote scheduling, signatures,
statistical significance, additional simulators, or production deployment.

Research: `docs/research/2026-10-14-reproducible-evidence.md`.
