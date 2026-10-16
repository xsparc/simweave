# PostgreSQL workers and Keycloak integration

SQLite remains the default. PostgreSQL is an opt-in suite queue and artifact
metadata backend; the API's catalog and legacy run database remain local SQLite.
Run one API catalog authority. This is not an automatic migration or an HA API.
Workers on separate machines need PostgreSQL and the same S3 bucket, not a shared
SQLite volume. Install `simweave[postgres,s3]` on each participant.

## PostgreSQL setup

Provision a dedicated database and an operator-controlled role. Set
`SIMWEAVE_POSTGRES_DSN` through your secret manager/environment; never put it in a
scenario, URL or CLI argument. For remote production databases use authenticated
TLS with `sslmode=verify-full` and a trusted server CA. The local integration
fixture alone uses plaintext PostgreSQL inside its isolated container network.

Initialize explicitly before starting clients:

```sh
simweave operations --database scratch/queue --postgres initialize
simweave operations --database scratch/queue --postgres worker --backend storage.json
```

`--database` supplies the local scratch directory anchor in PostgreSQL mode; it
is not a PostgreSQL file. Give each process writable local scratch. For the API,
set `SIMWEAVE_SUITE_BACKEND=postgres`, `SIMWEAVE_POSTGRES_DSN`,
`SIMWEAVE_ARTIFACT_BACKEND=storage.json`, and the existing API authentication
configuration. Every participant must select the same backend explicitly.
Filesystem artifact storage is rejected in PostgreSQL mode.

```json
{"schema_version":1,"endpoint":"https://objects.example","bucket":"simweave","region":"us-east-1"}
```

Provide `SIMWEAVE_S3_ACCESS_KEY` and `SIMWEAVE_S3_SECRET_KEY` separately. Optional
`ca_bundle` names an operator-controlled PEM trust bundle for a private CA; TLS
verification remains enabled. Objects retain the existing tenant/digest keys.

Claims use `FOR UPDATE SKIP LOCKED`; database time controls 30-second leases.
Completion and renewal require the current attempt token. Expired work becomes
`worker_lost`, with explicit retry (maximum five attempts). Execution is at least
once; stale workers cannot publish a successful job result. Unreferenced immutable
objects may remain after a failed publication. Admission enforces 1,000 active jobs
globally and 1,000 retained jobs per tenant; there is no weighted tenant fairness.
Each process has two bounded connection pools (up to 16 connections each); size
server connection capacity for the number of workers and APIs.

Maintenance pause/drain/resume and stopped-worker acknowledgement use the shared
database fence. Pause prevents new mutations and claims while active jobs finish.
SQLite checkpoint, backup, restore and artifact recovery commands deliberately
reject PostgreSQL. Before any manual native backup, pause and drain, stop all
writers, and coordinate PostgreSQL, object storage and local catalogs. A tested
cross-store PostgreSQL recovery/cutover procedure is still future work. Do not
switch an existing SQLite installation by changing one environment variable:
there is no automatic data transfer or rollback migration.

## Keycloak access tokens

Set `token_profile` to `keycloak` in the existing `SIMWEAVE_OIDC` JSON. The default
remains strict RFC 9068. Pin issuer, JWKS URI, API audience and permitted client
IDs. Map provider subject IDs to local tenant/role principals. Keycloak tokens
must have JWT header type, signed payload `typ=Bearer`, allowed `azp`, and the API
audience (including an audience array). ID tokens are rejected. Tenant and role
claims from the provider cannot override the local principal map.

Configure an audience mapper for `simweave-catalog`, retain the `basic` client
scope for subject IDs, and assign the appropriate `catalog:read`,
`catalog:import`, or `catalog:approve` scope. Use short access-token lifetimes
within the configured maximum. Provider key rotation requires retaining previous
public keys until their tokens expire; JWKS refresh follows the configured cache.

The fixture exercises service-account client credentials for two tenants and
three roles. It does not implement human login, refresh-token handling in the
browser, or immediate resource-server revocation. Provider logout/revocation makes
introspection inactive, but offline JWT validation still accepts an otherwise
valid token until expiry. Choose a revocation strategy before internet-facing use.

## Repeatable verification

`tests/test_postgres.py` runs only against the dedicated `simweave_test` database
named by `SIMWEAVE_TEST_POSTGRES_DSN`; it resets only that fixture schema's tables.
`scripts/check_keycloak.py` provisions synthetic realms on a loopback Keycloak
fixture. `scripts/check_distributed.py` owns temporary Docker services, 1,000 jobs,
eight workers on two isolated container hosts, verified TLS S3, worker loss and
restart/API checks. It removes its containers/network on exit. These container
hosts share one physical machine; timings are fixture observations, not an SLA.
See the provider/distributed CI workflow for pinned images and runnable setup.
