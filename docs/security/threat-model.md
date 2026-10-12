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
