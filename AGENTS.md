# SimWeave engineering

SimWeave is an independent MIT project in a multi-project workspace.

Read authority in this order: `docs/architecture/overview.md`,
`docs/roadmap/implementation-roadmap.md`, accepted files in
`docs/architecture/decisions/`, code and tests, then supporting documentation.
`docs/governance/project-evidence.toml` is a derived evidence index.

Use OpenSteward research before consequential design changes, deliver one bounded
slice at a time, and update traceability with actual verification results.
The initial three-slice MVP, public GitHub repository, commits, pushes, and pull
requests are authorized. Merging, releases, deployments, paid services, and
unrelated scope require separate authority. Routine maintenance may prepare draft
PRs with evidence; do not merge them autonomously.

Keep simulation math independent of HTTP, persistence, ROS, and UI dependencies.
Use explicit versioned contracts, tenant scoping, parameterized SQL, bounded work,
and fixed adapter registrations. No dynamic code, shell, arbitrary XML, or remote
asset loading from scenario input. Never claim cross-engine numerical identity.

Run `python -m pytest`, `ruff check .`, `ruff format --check .`, and
`python scripts/check_governance.py --as-of YYYY-MM-DD --strict` before closeout.
Run optional simulator tests when installed; report real ROS/container validation
gaps. Keep secrets, local paths, runtime databases, and private state out of Git.
