# Portable catalogs and team baseline API

Archives preserve build reports, environments, policies, approvals and comparisons.
Retain original telemetry bundles separately. Checksums detect corruption, not a
malicious author who recomputes them. Restore checks contracts, keys, references,
rollback policies and digests; it preserves statistical outputs without rerunning
inference or authenticating historical approval labels. Trust the archive custodian.

```sh
simweave history export --database history.sqlite3 catalog.ndjson
simweave history restore --database restored.sqlite3 catalog.ndjson
```

Both reject existing outputs. Canonical UTF-8 NDJSON v1 contains a format header,
ordered build/event/comparison records, then counts and SHA-256 of preceding bytes.
No SQL, paths, compression or execution. Limits: 100 builds, 1,000 events, 1,000
comparisons, approximately 4 MiB per record, 512 MiB total. Plan catalog rollover
before combined data exceeds the archive cap. Export uses one read transaction;
restore stages on the destination filesystem and publishes with a non-overwriting
hard link. NTFS/ext4 are verification targets; unsupported filesystems fail closed.
Atomic visibility does not guarantee recovery from every storage/power failure.

Configure private `SIMWEAVE_TOKENS` JSON. Existing token-to-tenant strings retain
run API permissions only. Catalog entries are objects:

```json
{
  "REPLACE_WITH_RANDOM_TOKEN_AT_LEAST_32_CHARS": {
    "tenant": "team-a", "subject": "reviewer-a", "role": "approver"
  }
}
```

Use distinct random credentials, never this example key. Keep the mapping private.
Configure reader/importer entries similarly. Write roles can read but neither
implies the other; catalog credentials have no run API access. Restart after token
changes. This is static bearer authorization, not OAuth/OIDC identity proof. Subjects
are operator-assigned audit identities; API requests cannot supply `approved_by`.

The operator-owned catalog directory derives from `SIMWEAVE_DB`; startup provisions
one catalog per tenant. SQLite stays single-host; do not use network filesystems.
For recovery, stop writers, restore a new path, verify, then explicitly cut over.
There is no HTTP restore or arbitrary database-path endpoint.

| Route under `/api/v1/catalog` | Permission | Behavior |
| --- | --- | --- |
| GET root | Any catalog role | Current generation, baseline and caller identity |
| GET `/builds`, `/events`, `/comparisons` | Any | `after=0`, `limit=20` pages; max 50 |
| GET `/builds/{label}` | Any | Full immutable snapshot |
| GET `/comparisons/{id}` | Any | Historical pinned decision |
| PUT `/builds/{label}?role=candidate` | Importer | `application/zip` evidence bundle |
| POST `/comparisons` | Importer | Build and optional pinned generation |
| POST `/promote` | Approver | Build, policy, expected_generation, reason |
| POST `/rollback` | Approver | to_generation, expected_generation, reason |

JSON mutations accept schema_version 1. Tenant, database and approval identity
body fields are rejected. Statuses: 401 missing authentication, 403 forbidden role,
404 missing tenant-owned object, 409 stale generation/invalid evidence/quota,
413 oversized body, 415 wrong upload type, 422 invalid contract, 429 capacity.
Re-read and review stale generations; do not automatically retry approvals.
Duplicate labels never overwrite. Comparison HTTP 201 means persisted; inspect
`statistics.exit_code` for its verdict.

Uploads stream at most 128 MiB into temporary storage, verify full recordings and
clean up on completion/failure. Two import/comparison operations may run per server
process; additional processes multiply that bound. Configure reverse-proxy TLS,
upload/request timeouts and rate limits before remote use. Ordinary JSON bodies
stay at 64 KiB. Long SQLite transactions may contend and return 409.

The standard-library client reads `SIMWEAVE_API_TOKEN`, requires HTTPS except
loopback, rejects redirects and does not print credentials:

```sh
python examples/catalog_client.py --url http://127.0.0.1:8765 show
python examples/catalog_client.py --url http://127.0.0.1:8765 import results/evidence.zip --build build-1
python examples/catalog_client.py --url http://127.0.0.1:8765 promote --build build-1 --policy examples/decision-policy.json --generation 0 --reason "Reviewed recordings"
```

Switch credentials between operations. The example bounds inputs but reads one
bundle into memory. Use a streaming client for larger workflows. OpenAPI is at
`/openapi.json`, interactive documentation at `/docs`.
