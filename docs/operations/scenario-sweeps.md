# Plan scenario sweeps

A sweep turns explicit parameter choices into an ordinary Suite. For example:

```json
{
  "schema_version": 1,
  "name": "Mass and damping",
  "scenario": {"name": "Cart"},
  "axes": [
    {"field": "robot.mass", "values": [1.0, 2.0]},
    {"field": "robot.damping", "values": [0.1, 0.3]}
  ],
  "seeds": [7, 3],
  "adapters": ["reference"],
  "baseline": {},
  "candidate": {"kp": 9.0}
}
```

```sh
simweave sweep sweep.json --output suite.json
simweave suite suite.json --output results
```

The first command only plans. Omit --output to print Suite JSON; existing output
files are never overwritten. `sweep-schema` prints the strict JSON Schema.
Review generated scenarios before execution or submission to existing suite APIs.

Allowed axes are robot.mass, robot.damping, robot.initial_position,
robot.initial_velocity and sensors.position_noise_std. Use 1..3 distinct axes,
1..8 unique finite values each, at most eight combinations. Values must also pass
the existing Scenario bounds. Cartesian order follows the written axes/values;
the last axis varies fastest. Scenario names retain the first 89 characters of
the base name and append ` [sweep-01]`, and so on. The actual values are retained
in each scenario; the Suite digest binds the complete generated plan.

Seeds, adapters, baseline/candidate controllers and regression gates use the
existing Suite semantics. They override the base scenario's corresponding fields
at execution. At most 64 runs and 200000 total simulation steps are admitted.
Input and output are capped at 64 KiB. Invalid plans emit no suite or result bundle.

Sweeps neither search for optimal controllers nor justify automatic promotion.
Repeated comparisons retain the existing statistical interpretation limits; adding
parameter combinations does not establish a family-wise confidence guarantee or
cross-engine numerical identity. No new simulator installation is performed.
