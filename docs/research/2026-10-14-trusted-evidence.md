# Accepted research: trusted team integrations

DirectionBriefV1, schema_version 1. baseline_commit:
`c3929f349670c9b9ed599d5dd16ab42085962112`. scanned_at: 2026-10-14.
Coverage: API identity, JWT security, signing-key lifecycle, artifact provenance
and GitHub verification. The maintainer accepted recommendations 1 and 2.

1. **OIDC-backed API access — adopt.**
   [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html) (October 2021) distinguishes
   access tokens from ID tokens and requires issuer, audience, signature and expiry
   validation. [PyJWT usage](https://pyjwt.readthedocs.io/en/stable/usage.html)
   (live 2.15.1 documentation, checked on scan date) provides maintained RSA/JWT
   verification. Confidence: high in contract semantics; medium in provider
   interoperability until integration testing. Relevance/alignment: explicit SaaS
   identity without trusting client tenant/role claims. Opportunity: short-lived
   credentials and signing-key rotation. Risks: issuer compromise, stale keys,
   confused token types and scope escalation. Cost: high. Roadmap delta: SW009
   optional pinned issuer and server-bound catalog subjects. Verify two tenants,
   real signatures, claim failures, scopes, rotation/removal and refresh failures.

2. **Signed artifact provenance — adopt.**
   [GitHub CLI verification](https://cli.github.com/manual/gh_attestation_verify)
   supports artifact verification and constraints on repository, workflow, source
   ref and commit. [The official attest action](https://github.com/actions/attest)
   generates signed build provenance and a portable Sigstore bundle. Source event
   date: live undated documentation checked on scan date; action v4 selected by
   resolved immutable revision. Confidence: high in supported enforcement, medium
   until real signing/verification completes. Relevance/alignment: portable evidence
   with explicit producer trust. Opportunity: distinguish corruption checks from
   provenance verification. Risks: compromised signer, overbroad policy, verifier
   dependency and changing files between verification and restore. Cost: medium.
   Roadmap delta: SW009 operator verification/restore plus synthetic CI signing.
   Verify real attestations and reject altered bytes, wrong repository/workflow/
   ref/commit; retain exact verified bytes through restore.

Overall recommendation: implement both accepted boundaries with fail-closed errors.
Evidence gaps: commercial IdP onboarding, browser login, production deployment,
offline trust-root distribution, durable attestation retention, human approval
signatures and compromised trusted builders. These remain outside SW009.
