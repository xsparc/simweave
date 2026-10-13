# SW006 evidence workflow validation

Validation date: 2026-10-14. Acceptance is defined by ADR 0004.
Implementation and verification are recorded separately from usability targets.

## Executed checks

Targeted evidence and regression checks passed: 53 tests. They exercise real
reference/MuJoCo recordings, corruption with recomputed checksums, preview fidelity,
unknown/traversal members, duplicates, symlinks, size limits, runtime mismatch
before execution, fixed container controls/cleanup, and hostile HTML names/CSP.

Browser review used a loopback static HTTP preview, without an API or simulator.
Three controlled workflows identified failures for reference seeds 7 and 42 and
MuJoCo seed 7. Export preparation took 1.026, 0.834, and 0.565 seconds respectively;
these are automation observations, not human task-completion estimates. The
selected seeds, adapters, failed gates, and JSON contents were checked in the UI.
Browser error/warning logs were empty.

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
