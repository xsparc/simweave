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
