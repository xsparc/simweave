# Trusted evidence validation

Date: 2026-10-14. Baseline: `c3929f349670c9b9ed599d5dd16ab42085962112`.

SW009 changes catalog authentication and operator provenance verification, not
simulation math or browser behavior. Implementation commit:
`864c369c52570758fdb6ad1824b3d0df1958a851`; subsequent evidence updates change docs only.

All 253 local tests passed, including installed MuJoCo and 63 new trust-boundary
tests. The 49 OIDC tests use actual RSA keys/signatures and a loopback HTTP JWKS
server. They cover two tenants/three roles, required/invalid claims, scopes,
signature/type rejection, single-flight cache refresh, rotation/removal, HTTP
failure/redirect/oversize rejection, operator configuration and actual catalog
import/approval attribution. Fourteen attestation boundary tests cover command
policy, timeout/error handling and snapshot-safe restore. Their mocked verifier
results are not treated as cryptographic validation.

Real verification completed in [Trusted evidence run 38564051544](https://github.com/xsparc/simweave/actions/runs/38564051544).
GitHub signed a synthetic catalog containing 100 builds, three approval events and
100 comparisons. The production verifier successfully restored it on Ubuntu, then
rejected wrong repository, workflow, source ref, source commit and modified bytes.
The retained archive/bundle were downloaded and the same five controls plus
byte-identical restore/re-export passed independently on Windows with GitHub CLI
2.95.0. This verifies Linux-to-Windows signed recovery; no production catalog or
human identity was used.

- Artifact SHA-256: `489d2a5d98c1f03f2bd7b85545895c757c62a6f68f58cffadfb6ada8951b51bb`.
- Sigstore bundle SHA-256: `566054ca58fcbaad2c92a91d16f76a933c1d7a6a04bc32271b681e5a33ca2a6f`.
- Policy: repository `xsparc/simweave`, workflow `.github/workflows/trusted-evidence.yml`,
  ref `refs/heads/codex/sw009-trusted-evidence`, source commit as recorded above.

Ruff lint/format, whitespace and static/dated strict governance passed. Source and
wheel builds succeeded; all 63 new tests also passed against the isolated installed
wheel. A fresh Linux container installed hash-pinned JWT/cryptography dependencies
and passed RSA and MuJoCo smoke checks without runtime network access. Portable
GitHub CI runs all three desktop OSes on Python 3.11/3.12; hosted statuses remain
visible in the PR. No new local live Gazebo run was needed for these auth/storage
changes; the existing native CI job remains enabled. The existing Starlette/httpx
deprecation warning is unchanged.

Residual boundaries: no commercial identity provider enrollment, browser login,
production deployment, offline trust-root distribution or instantaneous revocation.
Cached keys remain trusted until their configured expiry. Attestations authenticate
producer and bytes under the selected policy, not human approvals or physics.
Original telemetry retention and prior browser validation gaps remain unchanged.
