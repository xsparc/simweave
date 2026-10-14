# OIDC identities and signed catalog recovery

The catalog API accepts optional RFC 9068 access tokens. This is resource-server
integration with an existing OIDC/OAuth provider, not a login UI or an identity
provider. Configure `SIMWEAVE_OIDC` as private JSON:

```json
{
  "issuer": "https://identity.example/",
  "jwks_uri": "https://identity.example/keys",
  "audience": "simweave-catalog",
  "client_ids": ["approved-client"],
  "principals": {
    "provider-subject-id": {
      "tenant": "team-a", "subject": "reviewer-a", "role": "approver"
    }
  }
}
```

The provider must issue RS256 access tokens with `typ: at+jwt` (also accepts
`application/at+jwt`), a public JWKS `kid`, exact issuer and single string audience,
and `sub`, `client_id`, `jti`, integer `iat` and `exp`. Optional `nbf` is checked.
ID tokens, unsigned/HMAC tokens and token-supplied key URLs are rejected. Clients
obtain tokens from the provider and send `Authorization: Bearer ACCESS_TOKEN`.
The existing example client reads that token from `SIMWEAVE_API_TOKEN`.

Subject bindings select tenant, role and a stable audit alias. Token tenant/role
claims cannot override them. Preserve alias-to-issuer/subject mappings in operator
records; existing approval schemas retain the alias, not raw personal claims.
Reader requires `catalog:read`, importer `catalog:import`, approver `catalog:approve`.
Each writer can read; scopes cannot grant a different role from the subject binding.
Unknown subjects/clients and invalid tokens return 401; missing scope returns 403.
Both use Bearer error headers. Tokens never appear in diagnostics.

Defaults: maximum token lifetime 900 seconds (configurable 60–3,600), clock skew
30 seconds (0–30), JWKS cache 300 seconds (5–3,600). Tokens are checked on every
request. Key refresh is single-flight with a five-second cooldown, including
unknown-key attempts. New keys may take five seconds to become usable. Cached
removed keys remain valid until cache expiry; use short lifetimes/cache periods
for revocation-sensitive deployments. Expired-cache refresh failure fails closed.
There is no introspection or instantaneous token revocation.

Key retrieval uses only the operator URL, HTTPS, no redirects or ambient proxies,
five-second network timeout, 256 KiB and 32-key limits. RSA keys must be 2,048–8,192
bits. No discovery URL is taken from a token. Explicit `allow_insecure_loopback`
permits HTTP only on numeric loopback addresses for integration tests; keep it
false in deployed configuration. A reverse proxy still supplies TLS, request timeouts
and rate limits. Configure at most 100 subject bindings and 20 client IDs.

`SIMWEAVE_TOKENS` continues to work. It may be empty when OIDC is configured.
OIDC catalog tokens have no run API authority. Restart to apply issuer/binding
changes; no private provider secrets are required or stored by SimWeave.

## Verify an attested catalog

Install a current GitHub CLI with `attestation verify` and source-ref/source-digest
flags (validated with 2.95.0). The trusted executable path, GitHub.com and Sigstore
trust infrastructure are operator dependencies. Public trust material may be
fetched; this workflow does not claim offline verification.

Create a policy from trusted release/build information, not values copied blindly
from the archive or untrusted attestation:

```json
{
  "schema_version": 1,
  "repository": "xsparc/simweave",
  "workflow": ".github/workflows/trusted-evidence.yml",
  "source_ref": "refs/heads/main",
  "source_digest": "REPLACE_WITH_THE_EXPECTED_40_CHARACTER_COMMIT"
}
```

```sh
simweave attestation catalog.ndjson --bundle bundle.jsonl --policy trusted-policy.json
simweave attestation catalog.ndjson --bundle bundle.jsonl --policy trusted-policy.json --restore recovered.sqlite3
```

The verifier requires GitHub Actions' OIDC issuer and SLSA provenance v1, denies
self-hosted signers, and enforces repository, workflow, source ref and commit.
It snapshots the archive and bundle before verification, then restores those same
archive bytes. The destination must be new. Failed verification, missing tooling,
timeouts and malformed responses never publish a catalog. Output is a bounded
summary receipt containing hashes and policy, not the verifier's raw metadata.
Verification alone checks signed bytes; restore also checks the catalog structure.

Limits: archive 512 MiB, attestation bundle 4 MiB, policy 64 KiB, verifier timeout
60 seconds, accepted JSON result 8 MiB. Original recordings still require separate
retention. Unsigned `history restore` remains available for explicit local recovery;
it does not claim provenance. There is no HTTP route invoking external verification.

The trusted-evidence workflow signs a generated synthetic 100-build catalog on
pushes to main/codex branches in this repository. PR events and forks do not sign.
Privileged actions are revision-pinned and permissions are job-scoped. The CI
artifact includes catalog, Sigstore bundle, policy and verification results for
seven days. Production consumers should expect main and an independently reviewed
commit. A signed development-branch fixture is not a release or a human approval.
Attestations prove the producer/bytes under the chosen policy, not simulation
correctness or immunity to a compromised trusted workflow.
