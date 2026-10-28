# Compare sweep plans

## Directional sweep plan comparison

```sh
simweave sweep-diff before.json after.json --output changes.json
simweave sweep-diff before.json after.json --format html --output changes.html
simweave sweep-diff-schema
```

The first input is before and the second is after; all deltas are after minus before. An admitted comparison exits 0 whether or not plans differ; invalid input/I/O exits 2. Omit --output for stdout. JSON includes before/after snapshots, signed run/step/headroom changes, ordered adapter changes and identical_inputs. A zero count delta does not establish experiment equivalence.

Reports compare planned counts, not execution results, physics equivalence, availability, reservations or runtime estimates. Identical inputs means equal normalized Sweep digests. Internal report consistency is not proof of source provenance; comparisons must be generated from independently admitted inputs. No simulation, scheduling, optimization or baseline approval occurs.
