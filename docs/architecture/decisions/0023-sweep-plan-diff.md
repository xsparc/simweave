# Directional sweep plan comparison

Status: accepted, 2026-10-28.

## Decision

Implement the three SW025 handoff tasks: a strict version-1 plan-difference contract, bounded JSON CLI and standalone HTML. Revalidate both Sweep inputs and generated Suite plans; derive snapshots with normalized source/Suite identities, counts and remaining admission capacity. Deltas are after minus before. Added adapters follow after order; removed adapters follow before order. Validate internal report arithmetic and identity flags. `sweep-diff before.json after.json [--format json|html] [--output path]` caps each input and output at 64 KiB and creates files exclusively. `sweep-diff-schema` exposes the model schema. HTML escapes labels and uses existing fixed CSS with a restrictive hash-based CSP.

## Milestone items

3. Add the versioned directional plan-difference contract.
4. Expose bounded JSON comparison and schema commands.
5. Render offline HTML comparison with evidence identities.

## Acceptance

Direction reversal negates deltas; adapter additions/removals preserve declared order; identical inputs are explicit and changed experiments with equal counts are not called identical. Both mutated/over-budget sources fail before rendering. Contracts reject inconsistent summaries and noninteger schema versions. CLI rejects oversized inputs without output and never overwrites. HTML preserves JSON identities/counts, escapes hostile names and passes desktop/mobile checks.

## Limits

Reports compare planned counts, not execution results, physics equivalence, availability, reservations or runtime estimates. Identical inputs means equal normalized Sweep digests. Internal report consistency is not proof of source provenance; comparisons must be generated from independently admitted inputs. No simulation, scheduling, optimization or baseline approval occurs.
