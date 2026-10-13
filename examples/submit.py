"""Minimal SaaS/CI client using only Python's standard library."""

import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path

base = os.environ.get("SIMWEAVE_URL", "http://127.0.0.1:8000").rstrip("/")
token = os.environ["SIMWEAVE_TOKEN"]
scenario = json.loads(Path(sys.argv[1]).read_text())


def request(path, body=None):
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers.update({"Content-Type": "application/json", "Idempotency-Key": uuid.uuid4().hex})
    req = urllib.request.Request(
        base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


run = request("/api/v1/runs", scenario)
deadline = time.monotonic() + 120
while run["status"] in {"queued", "running"}:
    if time.monotonic() > deadline:
        raise SystemExit("Timed out waiting for the worker; the run may still complete.")
    time.sleep(0.5)
    run = request(f"/api/v1/runs/{run['id']}")
print(json.dumps(run, indent=2))
raise SystemExit(0 if run["result"] and run["result"]["passed"] else 1)
