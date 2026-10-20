"""Bounded operator audit of retained object bytes; never repairs or deletes evidence."""

import tempfile
from pathlib import Path

from simweave.artifacts import MAX_BUNDLE, digest_file, key


def validate_page(tenant, after, limit):
    if not isinstance(tenant, str) or not isinstance(after, str):
        raise ValueError("invalid audit page")
    key(tenant, "0" * 64)
    if after:
        key(tenant, after)
    if not isinstance(after, str) or type(limit) is not int or not 1 <= limit <= 25:
        raise ValueError("invalid audit page")


def audit(artifacts, tenant, *, after="", limit=10):
    validate_page(tenant, after, limit)
    rows = artifacts.inventory_page(tenant, after, limit)
    # Treat the index as data too. Invalid metadata fails before any object I/O.
    for digest, size in rows:
        if not isinstance(digest, str):
            raise ValueError("invalid retained artifact metadata")
        key(tenant, digest)
        if type(size) is not int or not 0 < size <= MAX_BUNDLE:
            raise ValueError("invalid retained artifact metadata")
    results = []
    for digest, size in rows[:limit]:
        try:
            with tempfile.TemporaryDirectory(dir=artifacts.scratch) as temporary:
                staged = Path(temporary) / "object"
                try:
                    artifacts.backend.get(key(tenant, digest), staged)
                    status = "verified" if digest_file(staged) == (digest, size) else "corrupt"
                except FileNotFoundError:
                    status = "missing"
        except ValueError:
            status = "corrupt"
        except (OSError, RuntimeError):
            # Includes unavailable S3 objects: never infer absence from access denial.
            status = "unavailable"
        results.append({"digest": digest, "expected_bytes": size, "status": status})
    counts = {
        status: sum(item["status"] == status for item in results)
        for status in ("verified", "missing", "corrupt", "unavailable")
    }
    return {
        "schema_version": 1,
        "tenant": tenant,
        "after": after,
        "checked": len(results),
        "counts": counts,
        "results": results,
        "next_after": results[-1]["digest"] if len(rows) > limit else None,
        "healthy": all(item["status"] == "verified" for item in results),
    }
