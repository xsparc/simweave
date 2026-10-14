# Statistical decisions and baseline history

Use this workflow after collecting representative independent paired seeds. It
compares changes within one scenario and simulator; it does not establish robot
safety, cross-simulator equivalence, or guaranteed statistical coverage.

## Analyze a verified bundle

Set a suite to 30 distinct seeds and one adapter. Thirty pairs consume 60 of the
64-run limit; run a separate suite for each adapter. Use nonzero sensor noise when
studying sensitivity to stochastic observations. Deterministic constant changes
remain descriptive and cannot estimate variation across unobserved conditions.

```sh
simweave suite examples/cart-statistics.json --output .simweave/paired
simweave statistics .simweave/paired/evidence.zip --policy examples/decision-policy.json --output decision
```

Open `decision/report.html` for a script-free, self-contained review, or consume
`decision/decision.json`. `simweave statistics-schema` exports the policy schema.
The reader verifies complete recordings before analysis. Output directories must
be new. Existing suite v1 inputs, bundles, service endpoints and reports are unchanged.

Choose practical absolute increase tolerances before inspecting results. The
example uses RMSE 0.02 metres and final error 0.01 metres; those example values are
not calibrated acceptance criteria for your robot. Other supported metrics are
maximum absolute position (metres) and control effort (newton-seconds). An increase
is worse under this policy; quality gates still apply even when a metric decreases.

The fixed `paired-percentile-mean-v1` algorithm sorts seeds, takes each paired
candidate-minus-baseline difference, samples whole pairs with replacement using a
private seeded Python `random()` stream, and computes the mean with `math.fsum`.
It selects linear 2.5th and 97.5th percentiles from 5,000 resamples by default.
Policy bounds allow 1,000–10,000 resamples and at most four metrics. JSON records
the algorithm, policy and digest, complete report digests, runtime provenance,
roles, seed membership, sample counts, intervals, gate failures and issues.

| Result | Rule | Exit |
| --- | --- | --- |
| Within tolerance | Every selected upper endpoint is at or below its tolerance, with no quality or individual suite regression failures | 0 |
| Regression | A selected lower endpoint exceeds tolerance, or a known quality / individual suite regression gate fails | 1 |
| Inconclusive | No known failure, but an interval overlaps tolerance, fewer than 30 pairs, constant differences, incomplete/mismatched inputs or differing runtimes | 2 |

Invalid input/operational errors also return 2, with an error JSON on stderr.
No missing seeds are silently dropped: incomplete populations have no interval.
Singletons and constant differences may display descriptive intervals but never
pass a statistical decision. Known failures take precedence over uncertainty.
Different OS/architecture/Python/dependencies or recorded engine/adapter versions
confound a build comparison. Source revisions and implementation hashes may differ
because testing changed implementation is the purpose of build history.

Intervals are approximate and marginal, not a joint guarantee across metrics,
scenarios or repeated candidate builds. Unique seeds do not prove independence or
representativeness. There is no correction for multiple testing, sequential peeking
or selecting the best build. Select validation populations and policy beforehand;
retain a separate evaluation population when repeatedly tuning controllers.

## Approve an immutable baseline

The catalog is local operator state on a local filesystem. It is separate from the
service run database and has no HTTP endpoint or tenant/identity claims.

```sh
simweave history init --database .simweave/baselines.sqlite3
simweave history add approved/evidence.zip --database .simweave/baselines.sqlite3 --build approved-001 --role candidate
simweave history promote approved-001 --database .simweave/baselines.sqlite3 --policy examples/decision-policy.json --expected-generation 0 --approved-by reviewer --reason "Reviewed recovery population and policy"
simweave history add candidate/evidence.zip --database .simweave/baselines.sqlite3 --build candidate-001
simweave history compare candidate-001 --database .simweave/baselines.sqlite3 --generation 1 --output candidate-decision
simweave history show --database .simweave/baselines.sqlite3 --output baseline-history
```

Import validates a bounded snapshot of the full bundle and records its SHA-256,
report, environment and selected role. Default role is `candidate`; `--role baseline`
explicitly selects a suite's baseline controller instead. Cross-build comparisons
use each build's selected role, matching scenario name, adapter, seed and physical
inputs; the candidate bundle's internal baseline never replaces the approved build.
The approval's statistical policy applies across builds. Original suites' individual
regression gates apply to standalone statistics; cross-build history uses the pinned
policy plus each selected recording's quality gates.

Promotions require all selected recordings to be complete with passing quality
gates. They deliberately require an explicit command, reason, approval label, policy
and expected generation. Approval labels are unsigned operator assertions. A
statistical pass does not grant permission or change the active baseline. Review
inconclusive results and statistical assumptions before approving.

```sh
simweave history promote candidate-001 --database .simweave/baselines.sqlite3 --policy examples/decision-policy.json --expected-generation 1 --approved-by reviewer --reason "Reviewed candidate evidence"
simweave history rollback --database .simweave/baselines.sqlite3 --to-generation 1 --expected-generation 2 --approved-by reviewer --reason "Restore previous approved build and policy"
```

Rollback creates generation 3 referring to generation 1's exact build and policy.
Earlier events and comparisons remain intact. An explicit `--generation` pins an
approval; omission resolves the current approval once and records its generation.
Concurrent stale promotions fail instead of overwriting another approval.

## Retention, interoperability and limits

Build labels cannot be replaced; there is no update/delete command. SQLite triggers
also reject ordinary updates/deletes. Canonical record digests detect accidental
changes on read. A local operator with database access can bypass these controls;
the catalog is not a signed audit log or a hostile-tenant security boundary.

Retain original bundles separately: the catalog stores verified summaries and
bundle digests, not full telemetry. Stop catalog writers before copying its SQLite
file for backup. Keep the database and its journal together during recovery. Do not
use network-mounted SQLite or use this database as an upload format. Exported JSON
and HTML are portable read-only evidence; future hosted integration needs separate
tenant authorization, transactional storage and artifact retention.

Limits: 100 builds, 1,000 approval events, 1,000 saved comparisons per catalog,
approximately 4 MiB per build snapshot, existing 128 MiB bundle limits, and at most
32 seeds per scenario/adapter. `show` validates reports one at a time and exports
bounded metadata/results. Repeating `compare` appends another observation. If a
limit is reached, archive the catalog and explicitly initialize a new one; no
automatic eviction or hidden baseline replacement occurs.

Native acceptance can be reproduced with
`python scripts/check_decisions_ci.py --output decision-check --source-revision COMMIT_SHA`.
It verifies reference/MuJoCo 30-seed positive/negative controls and 20 separately
recorded controller candidates from one code revision. The ROS-enabled CI image
runs `--adapters gazebo --history-builds 0` for real Gazebo coverage.
