"""Durable queue consumer. Run separately from the HTTP service."""

from __future__ import annotations

import logging
import time
import uuid

from simweave.engine import execute
from simweave.store import LostClaim, Store

log = logging.getLogger(__name__)


def work_once(store: Store) -> bool:
    worker = uuid.uuid4().hex
    job = store.claim(worker)
    if not job:
        return False
    batch = []
    last_flush = time.monotonic()

    def sink(sample):
        nonlocal last_flush
        batch.append(sample)
        if len(batch) >= 256 or time.monotonic() - last_flush >= 1:
            store.append(job["id"], worker, batch)
            batch.clear()
            last_flush = time.monotonic()

    try:
        result = execute(job["scenario"], sink)
        store.append(job["id"], worker, batch)
        store.finish(job["id"], worker, result)
    except LostClaim:
        log.info("run claim ended: %s", job["id"])
    except Exception as exc:
        # Persist categories only; simulator errors may include private host paths.
        error = "adapter_unavailable" if isinstance(exc, ImportError) else "execution_failed"
        store.finish(job["id"], worker, None, error)
        log.warning("run failed: %s (%s)", job["id"], error)
    return True


def work_forever(store: Store) -> None:
    try:
        while True:
            if not work_once(store):
                time.sleep(0.5)
    except KeyboardInterrupt:
        return
