# Trusted evidence validation

Date: 2026-10-14. Baseline: `c3929f349670c9b9ed599d5dd16ab42085962112`.

SW009 changes catalog authentication and operator provenance verification, not
simulation math or browser behavior. Verification is in progress before draft PR.

Observed local checks: 41 OIDC tests with actual RSA keys/signatures and a local
HTTP JWKS server passed. They cover two tenants/three roles, invalid claims and
scopes, signature/type rejection, bounded cache refresh, rotation/removal, HTTP
failure/redirect/oversize rejection, and operator configuration. Fourteen attestation
boundary tests passed, including command policy, timeout/error handling and
snapshot-safe restore. Mocked verifier tests do not claim cryptographic attestation
validation; real GitHub-generated evidence is checked separately by CI.

Residual boundaries: no commercial identity provider enrollment, browser login,
production deployment, offline trust-root distribution or instantaneous revocation.
Cached keys remain trusted until their configured expiry. Attestations authenticate
producer and bytes under the selected policy, not human approvals or physics.
Original telemetry retention and prior browser validation gaps remain unchanged.
