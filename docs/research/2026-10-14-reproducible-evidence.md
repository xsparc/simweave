# Accepted research: reproducible evidence

DirectionBriefV1; schema_version: 1. Baseline:
`2173cd68aac61930e6f36e229e71762951f894c3`. Scanned: 2026-10-14.
Coverage: approved CI evidence/review needs, simulator repeatability, container
portability, archive security, offline browser security, GitHub artifact delivery.
The maintainer approved the prior recommendations 1 and 2 for SW006.

| Finding and source | Source event date | Confidence / relevance / alignment | Opportunity or risk / cost | Disposition / roadmap delta / verification |
| --- | --- | --- | --- | --- |
| MuJoCo scopes exact repeatability to version and architecture; OS changes can alter results. [MuJoCo computation](https://mujoco.readthedocs.io/en/stable/computation/index.html#reproducibility) | Undated live documentation, checked 2026-10-14 | High / direct / portable experiments | Runtime fingerprint and exact-image reruns; medium | adopt / SW006 / compare actual telemetry, expose mismatch |
| Docker supports no-pull execution and explicit isolation/resource controls. [Docker run](https://docs.docker.com/reference/cli/docker/container/run/) | Undated live documentation, checked 2026-10-14 | High / direct / operator-controlled execution | Reuse a retained image without trusting bundle-selected code; medium | adopt / SW006 / real container rerun and command-boundary tests |
| ZIP extraction needs inspection; caller-managed paths are unsafe without validation. [Python zipfile](https://docs.python.org/3/library/zipfile.html) | Undated live documentation, checked 2026-10-14 | High / direct / bounded contracts | Fixed member names, checksums, size limits, no extraction; medium | adopt / SW006 / adversarial archives and corrupt telemetry |
| CSP hashes admit specific inline scripts without allowing arbitrary inline code. [MDN script-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src) | Undated live documentation, checked 2026-10-14 | High / direct / portable review | Self-contained report with escaped data and no network; medium | adopt / SW006 / hostile names, actual file-open browser checks |
| Workflow artifacts preserve job outputs for later inspection. [GitHub artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts) | Undated live documentation, checked 2026-10-14 | High / direct / SaaS interoperability | Include reports and bundles with existing CI outputs; low | adopt / SW006 / artifact contents and CI execution |

Overall recommendation: implement the approved evidence workflow with explicit
unknown provenance and retained-image requirements. Evidence gaps: image retention
is operator-managed; unsigned metadata is not authentication; no representative
human usability study or cross-machine determinism guarantee.
