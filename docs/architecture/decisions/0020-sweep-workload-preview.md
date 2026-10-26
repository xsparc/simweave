# Sweep workload preview

Status: accepted, 2026-10-26.

## Decision

Add plan-only sweep-inspect and sweep-inspect-schema commands plus inspect_sweep. Revalidate the Sweep and admit its generated Suite before counting the actual expansion. Emit a closed version-1 JSON report with sweep/suite digests, scenario count, aggregate runs and steps, and parameter/adapter points with ordered seeds and counts. Each seed includes baseline and candidate runs. Use existing 64 KiB input/output caps and exclusive output creation. Preserve the existing sweep command and all execution admission limits.

## Acceptance

Counts independently equal expanded runs/steps for multiple axes/adapters/seeds; ordering and suite identity match the planner; no simulation is invoked; over-budget, invalid and mutated inputs fail; schema version is strict; CLI byte bounds and exclusive output hold.

## Limits

Counts are planned work, not wall-clock, memory, storage or monetary estimates. A valid plan does not establish installed adapter availability or successful execution. Rejected over-budget plans produce no partial report. Reports are unsigned derived evidence; execution must independently validate the Suite. No queue scheduling, simulation, automatic optimization or baseline decision occurs.

