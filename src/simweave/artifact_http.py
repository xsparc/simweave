"""Verified snapshots with bounded download concurrency and response cleanup."""

import tempfile
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import HTTPException
from fastapi.responses import FileResponse


class Download(FileResponse):
    def __init__(self, path, cleanup):
        super().__init__(path, media_type="application/zip", filename="evidence.zip")
        self.cleanup = cleanup

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.cleanup()


class Downloads:
    def __init__(self, artifacts):
        self.artifacts = artifacts
        self.slots = BoundedSemaphore(2)

    def response(self, tenant, digest):
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "artifact download capacity reached")
        temporary = None

        def cleanup():
            try:
                if temporary:
                    temporary.cleanup()
            finally:
                self.slots.release()

        try:
            temporary = tempfile.TemporaryDirectory(dir=self.artifacts.scratch)
            target = Path(temporary.name) / "evidence.zip"
            self.artifacts.get(tenant, digest, target)
            return Download(target, cleanup)
        except KeyError:
            cleanup()
            raise HTTPException(404, "retained artifact not found") from None
        except Exception:
            cleanup()
            raise HTTPException(503, "artifact unavailable or failed verification") from None
