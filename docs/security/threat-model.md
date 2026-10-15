# Security and trust boundaries

Scenarios and stored metadata are untrusted input. Accept only closed versioned
schemas and built-in models/controllers; reject non-finite numbers, unknown
fields, excessive horizons, arbitrary imports, XML, paths, and remote assets.
Simulation here is for software experiments, not a safety certification or a
controller for physical hardware.

The HTTP service requires a token mapping. Resolve tenants server-side and use
tenant-scoped SQL for every user-accessible object. The API does not accept tenant
headers as identity. Do not log tokens, scenario bodies, or raw internal errors.
Bind the quickstart to loopback. Network deployments need TLS and gateway rate
limits. Browser scripts render user content as text and retain tokens only in
memory. No wildcard CORS or outbound webhook destinations are configured.

SQLite and bearer tokens are suitable for a trusted single-host MVP. The operator
can read local state; this is not isolation against a malicious host. Worker
processes share database access and must be trusted. Untrusted simulator plugins,
distributed workers, account onboarding, OIDC, encryption at rest, and billing are
deferred. Hosting for hostile tenants requires a separate deployment review.

SHA-256 digests detect accidental artifact changes when compared with trusted
metadata. They are not signatures and do not stop an attacker who can rewrite
both telemetry and its metadata. Replay checks recording consistency, not physics.

The optional ROS/Gazebo fixture launches a fixed executable from the trusted ROS
installation. Every experiment uses a new namespace, transport partition, private
temporary working directory, and headless world. Only bounded numbers enter the
generated SDF. No API input can choose executable paths, native plugins, models,
ROS namespaces, or remote assets. The child receives an allowlist of runtime
environment variables; API tokens are not forwarded. Gazebo owns real native
physics, so installation and resource quotas remain operator responsibilities.

Namespaces and partitions prevent accidental cross-run interference; they are
not authentication against other processes on the DDS domain. Use trusted local
ROS networks or isolated workers. Verification runs non-root without external
networking. RPC deadlines abort uncertain mutations without retries. Closing a
run terminates and reaps its fixture, escalating to kill after five seconds;
Linux parent-death signaling terminates the fixture if the worker dies. ROS
services are not a public SaaS boundary or an OS security sandbox.

Suite documents cannot select executable code, artifact paths, or remote assets.
Output case paths are generated internally in a new operator-selected directory.
Reports are unsigned user-controlled summaries. The authenticated report endpoint
accepts at most 4 MiB, 64 matrix cases, and 101 preview points per completed case;
other request bodies retain the 64 KiB limit. It validates consistency without
reading local files, executing scenarios, or inserting runs. Comparison queries
resolve both tenant-owned IDs before accessing telemetry. Browser text uses safe
DOM text assignment; JSON exports contain no session token.
## Portable evidence and reruns

Evidence ZIPs are untrusted data. Bound the central directory before ZIP parsing,
then enforce member counts, sizes, compression methods, exact filenames, SHA-256
checksums, recording integrity, and preview fidelity. Never extract archive paths.
Reject symlinks, duplicates, extra entries, and executable payloads. Checksums and
operator-supplied revision/image labels are not signatures or authentication.

Offline HTML escapes data and uses text-only DOM construction plus hash-based
script/style CSP with no network access. It contains bounded previews, not raw
telemetry, tokens, or an API connection. A modified HTML file can also modify its
CSP; treat untrusted producers accordingly. Review scenario names/inputs before
sharing because they are deliberately part of the artifact.

The local CLI container rerun is separate from the service. It requires a trusted
operator-selected full local image ID matching recorded provenance, never pulls,
and uses a fixed command with no host mounts or socket. Containers run unprivileged
with network disabled, dropped capabilities, resource limits, and an execution
deadline. The image/entrypoint and Docker daemon remain trusted. Validate actual
installed code/dependencies before executing and report numerical divergence even
when fingerprints match. No source or script from the bundle is executed.

## Regression decisions and baseline approvals

Statistical work is bounded by validated policies and matrix limits. Decisions
cannot execute arbitrary estimators or promote builds. Missing seeds, incompatible
inputs, constant differences and small populations cannot silently become a pass.
Marginal intervals assume representative independent seeds and do not correct for
repeated testing. A misleading population or dishonest producer can still create
misleading evidence; recording verification does not validate experiment design.

The local history CLI snapshots and validates bundles before import. Parameterized
SQL, immediate transactions and expected generations prevent accidental injection
and stale approval updates. Immutable rows, pinned policies and content digests
preserve the application history, not resistance to a malicious local administrator.
Local CLI approval labels/reasons are assertions, not authenticated identities. Keep
private operator information out of artifacts intended for sharing. Never accept
arbitrary SQLite database uploads. Original
recordings require separate retention. New script-free reports escape evidence
text and restrict scripts, network requests and external assets through CSP.

## Team evidence boundary

The catalog API derives tenant, subject and role from operator-controlled bearer
configuration. Each tenant has a separate server-selected catalog. Reader cannot
mutate; importer cannot approve; approver cannot import. Catalog credentials cannot
use the run API. Old string token mappings cannot access catalogs. Every object
lookup uses the caller's catalog, and request bodies cannot override identity.
Subjects remain static operator assignments, not OIDC identities or signed human
approvals. Shared credentials lose individual attribution; restart after rotation.

Uploads stream to temporary storage, enforce 128 MiB, and verify full recordings.
Two imports/comparisons per process bound expensive concurrency; multiple processes
multiply the bound. A reverse proxy must constrain duration, rate and TLS for remote
deployment. Catalog quotas and 64 KiB JSON limits constrain growth. Authenticated
users can still consume their quotas, and a compromised importer can submit
misleading evidence. Explicit approver review remains necessary.

Archive restore never executes SQL or extracts paths. Canonical records, checksums,
quotas, generation/reference checks and fresh staging prevent accidental corruption
from becoming an active catalog. Hard-link publication rejects existing destinations.
Checksums are not signatures; a malicious custodian can forge records and decisions.
Restore does not authenticate original approvals or rerun statistical computation.
Catalog filesystem access remains trusted operator authority. No HTTP restore exists.

## OIDC and provenance trust

Optional OIDC catalog authentication accepts only the configured issuer, audience,
approved clients, subject bindings, access-token type and RS256 public keys.
Signature/lifetime checks precede authorization. Token roles and tenant claims
cannot override server mappings; role scopes narrow authority. ID tokens cannot
be substituted for access tokens. OIDC does not grant run API permissions. Raw
claims/tokens and key-fetch exceptions are excluded from API diagnostics.

HTTPS JWKS retrieval disables redirects and ambient proxy discovery, uses only an
operator-configured URI, and bounds time/bytes/key count/key size. Single-flight
refresh and cooldown constrain unknown-key traffic. Expired-cache failures deny
access, but a removed key can remain valid until cache expiry; this is not immediate
revocation. Issuer compromise, stolen valid bearer tokens and unsafe operator
bindings remain material risks. Loopback HTTP is opt-in for synthetic integration
tests, not a production transport. No provider credentials are read or stored.

The operator attestation command delegates cryptographic verification to GitHub CLI
under repository, workflow, source-ref and commit constraints. The verifier binary,
GitHub/Sigstore trust roots and selected producer are trusted. Input snapshots bind
verification and restore; errors/timeouts/malformed results fail closed. Raw verifier
output is not returned. Input sizes, accepted result size and execution time are
bounded. The verifier writes stdout to temporary disk before its result-size check.
There is no externally callable subprocess route or arbitrary command parameter.

Only synthetic catalogs are signed by the CI verification workflow. Signing runs
on repository push events with pinned privileged actions and job-scoped rights,
not pull-request events or forks. Trust policy must independently pin the intended
ref and commit; a valid development-branch signature is not a release approval.
Signatures do not authenticate historic human approval labels or establish physical
correctness. A compromised trusted builder can still issue misleading provenance.
# Durable suite storage boundary

Suite execution retains fixed adapter registration and bounded contracts. Run
tokens schedule only their configured tenant; catalog identity grants no execution
authority. Unique attempt claims and expiry fence cancelled/stale workers. Artifact
keys derive only from validated tenants and content digests; upload verification
uses a bounded snapshot. Operators select backends, never HTTP clients. S3 uses
explicit credentials, HTTPS outside loopback and conditional create-only writes.
No delete/GC path exists. External lifecycle policies, disk exhaustion, backend
loss and orphaned uploads remain operational risks. Quiesce workers/submissions
for paired metadata backups; independently protect artifact bytes and metadata.
