# Regression suites and comparisons

Use suites to evaluate controller tuning across scenarios, seeds, and simulators.
Each pair uses the same physical inputs, sensor noise seed, and quality gates.
Controllers differ only in PD gains or force limits; changing the target would
change the experiment and is rejected. Each simulator is evaluated separately.

## Run a suite

`examples/cart-regression.json` runs two controllers across ten seeds on both
MuJoCo and Gazebo: 40 runs. Use the ROS-enabled environment described in
`ros2.md`, or run it in the integration image:

```sh
docker build -f integrations/ros2/Dockerfile -t simweave:regression .
docker run --name simweave-suite --network none --pids-limit 256 --memory 4g --cpus 2 \
  simweave:regression simweave suite examples/cart-regression.json --output /workspace/results
docker cp simweave-suite:/workspace/results ./regression-results
docker rm simweave-suite
```

For a quick local run, copy the example and set `adapters` to `["reference"]`
or `["mujoco"]` (requires the optional MuJoCo installation). Then:

```sh
simweave suite my-suite.json --output .simweave/regression
simweave replay .simweave/regression/case-0000
simweave suite-schema
```

The matrix overrides each scenario's adapter, seed, and entire controller. Scenario
names must be unique. Maximums: eight scenarios, 32 unique seeds, three adapters,
64 expanded runs, and 200,000 total steps; these constraints all apply together.
Input is limited to 64 KiB. Runs execute sequentially, without queueing or retries.
An unavailable adapter is an error, never a skip. Existing output directories are
not overwritten. A storage failure or interruption may leave partial artifacts;
do not treat an absent final report as success.

Output includes:

- `suite.json`: normalized input and explicit controller definitions.
- `report.json`: complete case summaries, suitable for opening in the dashboard.
- `summary.json`: pair comparisons, signed metric changes, and aggregate exit code.
- `junit.xml`: per-run quality gates and per-pair metric-increase checks.
- `report.html`: self-contained review with failure navigation and pair export.
- `environment.json`: bounded runtime/dependency fingerprint and optional revision/image ID.
- `evidence.zip`: checked portable data bundle containing all complete recordings.
- `case-NNNN/`: scenario, full-resolution telemetry, and result when execution
  completed. Failed execution may leave partial telemetry without a result.

Exit 0: every baseline, candidate, and regression gate passed. Exit 1: at least
one quality/regression gate failed. Exit 2: input, execution, or storage failure.
Individual execution failures still allow other cases to finish and be reported.
A failing baseline fails the suite even if the candidate passes. Regression gates
specify an absolute maximum increase, in the metric's units, rather than a ratio:
`candidate - baseline <= max_increase`. They are optional and explicit; numeric
changes alone do not imply a statistically significant improvement or regression.

## Inspect and export a regression

For service-free review, open `report.html` and follow the three steps shown on
the page. The [evidence guide](evidence.md) covers offline exports, bundle
verification, and exact-image reruns. The existing connected dashboard workflow
below remains available for workspace runs and older JSON reports.

Start `simweave demo` and open its dashboard. In **Baseline & candidate**, choose
two completed workspace runs and click **Compare runs**, or select the CLI suite's
`report.json` in **Open suite report**. Loading reports requires a connected API
but no installed simulators. It creates no runs and never accesses artifact paths.

Suite reports initially select the first failing pair. **Next failing pair** cycles
through failures and execution errors. Read baseline/candidate PD gains, overlaid
positions, all four metric deltas, and gate outcomes. **Next failing gate** focuses
each failure, including a failed baseline. **Export comparison JSON** saves the
selected pair and source identifiers. For recording playback, use the full case
directory with the CLI, or **Export JSONL** on an individual workspace run.

The overlay uses at most 101 evenly spaced samples per trajectory, including both
ends. Full-resolution telemetry determines metrics and gates. Short transients
can be absent from the plot; use the full recording for detailed investigation.
Both traces have different colors and line styles, and gate states also use text.
Comparison exports contain summaries, not replayable recordings or signatures.

Workspace comparisons verify both recordings before showing them. Imported suite
reports validate shape, matrix membership, digests of scenarios, result/gate
consistency, and preview clocks; they cannot verify omitted telemetry. Treat them
as unsigned input. Runtime version differences produce a warning. Matching version
strings do not prove matching platform/hardware or validate the original physics.

## CI integration

Run `simweave suite` as a normal CI command and retain the output directory even
when its exit status is nonzero. Do not use `continue-on-error` for production
quality gates. Upload the complete directory so failed pairs can be inspected and
their recordings replayed.

This repository's `scripts/check_regression_ci.py` verifies both a passing suite
and an intentionally degraded controller (`kp=kd=0`). The negative fixture is
expected to return 1; the check fails if it returns 0 or 2. It also verifies every
recording. GitHub CI runs ten seeds on MuJoCo, and the ROS job runs ten seeds on
both MuJoCo and Gazebo, retaining JSON, JUnit, and recordings for seven days.
The same artifacts now include offline HTML, environment metadata, and evidence
ZIPs. The ROS job also reproduces a known failure in a fresh retained image and
checks exact telemetry/result equality for all three installed adapters.
