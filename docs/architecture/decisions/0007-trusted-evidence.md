# ADR 0007: OIDC access tokens and attested catalog recovery

Status: accepted

Date: 2026-10-14

The maintainer accepted recommendations 1 and 2 after PR13's squash merge.
Baseline: `c3929f349670c9b9ed599d5dd16ab42085962112`.

## Scope and decision

Add optional catalog authentication using RFC 9068 JWT access tokens from one
operator-pinned OIDC issuer/JWKS endpoint and audience. Require RS256, explicit
access-token type, signature, expiry, issue time and bounded lifetime. Do not use
ID tokens as API credentials. Map verified subjects to existing tenant/role/audit
identities through operator configuration; intersect role authority with token
scopes. Token claims cannot select tenants or elevate roles. Preserve static token
compatibility and keep catalog credentials separate from run API credentials.

Cache bounded public keys with single-flight refresh and cooldown. Reject unknown
keys and expired-cache failures; never follow token-provided key URLs or redirects.
HTTPS is mandatory except an explicitly enabled loopback integration-test mode.
Use PyJWT/cryptography rather than implementing signature verification.

Add operator CLI attestation verification and verified restore. Delegate Sigstore
certificate, signature, transparency and provenance checks to GitHub CLI. Pin
GitHub.com, repository, signer workflow, source ref and source commit in an explicit
versioned policy; deny self-hosted signers. Snapshot bounded input files so the
verified archive is the exact archive restored. A nonzero verifier result, timeout,
missing tool or malformed result fails closed. No HTTP subprocess endpoint exists.
Retain unsigned local recovery as an explicit separate command for compatibility.

CI signs only a synthetic catalog on repository push events, with job-scoped
attestation/OIDC permissions. Pull-request events do not sign. Verify the real
attestation and negative controls; retain the archive and bundle as CI artifacts.
Attestations establish producer identity and artifact integrity, not physics
correctness or human approval. Signing synthetic verification evidence is part of
this slice's verification; no release, deployment or production data is involved.

## Acceptance and verification

- Two tenants and all three roles: valid tokens, missing scopes, privilege spoofing,
  wrong issuer/audience/signature/type, expiry, future timestamps and oversized input.
- Exercise real RSA signatures, local HTTP JWKS integration, caching, rotation,
  key removal, refresh failure and unknown-key request bounds.
- Verify a real GitHub-attested catalog, restore it, and reject byte tampering,
  wrong repository/workflow/ref/commit. Test subprocess bounds and fail-closed paths.
- Full portable suite, optional installed simulator checks, package builds, lint,
  static and dated governance, and Windows/Linux verification where available.

Expected paths: auth/config/catalog API, attestation CLI, tests, lockfiles, CI,
examples and governance. Risks: issuer compromise, stale cached keys, stolen bearer
tokens, signer trust, verifier availability and TOCTOU. Non-scope: browser login,
IdP provisioning, refresh-token storage, distributed storage/jobs, automatic approval,
production deployment, new simulators and human-signature claims.

Research: `docs/research/2026-10-14-trusted-evidence.md`.
