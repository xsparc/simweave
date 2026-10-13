"""Measure engine throughput on this environment; no universal performance claim."""

import argparse
import json
import statistics
import time
import tracemalloc

from simweave.contracts import Scenario
from simweave.engine import execute

parser = argparse.ArgumentParser()
parser.add_argument("--adapter", choices=["reference", "mujoco"], default="reference")
parser.add_argument("--steps", type=int, default=20_000)
parser.add_argument("--repeats", type=int, default=3)
args = parser.parse_args()
if not 1 <= args.repeats <= 10:
    parser.error("repeats must be between 1 and 10")
scenario = Scenario.model_validate({"adapter": args.adapter, "world": {"steps": args.steps}})
durations = []
tracemalloc.start()
for _ in range(args.repeats):
    start = time.perf_counter()
    result = execute(scenario, lambda sample: None)
    durations.append(time.perf_counter() - start)
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
median = statistics.median(durations)
print(
    json.dumps(
        {
            "adapter": args.adapter,
            "steps": args.steps,
            "repeats": args.repeats,
            "median_seconds": round(median, 4),
            "steps_per_second": round(args.steps / median),
            "peak_python_bytes": peak,
            "telemetry_digest": result.telemetry_digest,
        },
        indent=2,
    )
)
