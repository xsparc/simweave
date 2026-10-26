# Preview sweep workload

```sh
simweave sweep-inspect sweep.json --output workload.json
simweave sweep-inspect-schema
```

Omit --output to print JSON. Successful inspection exits 0; invalid input exits 2
without a workload report. Files are created exclusively. Input/output use the
existing 64 KiB cap. The source must pass all Sweep and generated Suite rules,
including at most 64 runs and 200000 total steps.

A version-1 report lists scenario count, total runs and simulation steps, sweep
and suite SHA-256 identities, and one point per parameter/adapter combination.
Point counts include both baseline and candidate for every listed seed. For example,
four parameter combinations, two adapters and two seeds plan 32 runs. At ten
steps per run the preview reports 320 steps. Adapter and seed order are retained.

Counts are planned work, not wall-clock, memory, storage or monetary estimates. A valid plan does not establish installed adapter availability or successful execution. Rejected over-budget plans produce no partial report. Reports are unsigned derived evidence; execution must independently validate the Suite. No queue scheduling, simulation, automatic optimization or baseline decision occurs.


## Sweep capacity report

```sh
simweave sweep-inspect sweep.json --format capacity-json --output capacity.json
simweave sweep-inspect sweep.json --format html --output capacity.html
```

Omit `--output` to print the selected format. The original default JSON and `sweep-inspect-schema` remain unchanged. Capacity JSON nests the original report under `workload`, adds `max_runs` (64), `max_steps` (200000), remaining counts and adapter rows. Counts include both controllers for each seed. A 16-run, 160-step plan has 48 runs and 199840 steps of remaining admission capacity. HTML shows the same counts, parameter points and sweep/suite identities.

Capacity is planned admission headroom, not reserved resources, adapter availability or a time/memory/storage/cost estimate. No simulation, queue scheduling or baseline decision occurs. Reports are unsigned derived evidence; execution independently validates its input.
