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

