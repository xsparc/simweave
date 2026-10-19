"""Verified immutable object reuse for operator-local checkpoints."""

import os
import tempfile
from pathlib import Path

from simweave.artifacts import digest_file, publish


def no_links(path: Path):
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ValueError("checkpoint cache links are forbidden")


def validate_cache(cache, target, artifacts, catalogs, queue):
    no_links(cache)
    resolved = cache.resolve()
    # An operator-owned cache must be separate from source state and publication.
    protected = [target, catalogs, artifacts.db.path, queue]
    if hasattr(artifacts.backend, "root"):
        protected.append(artifacts.backend.root)
    for path in protected:
        path = path.resolve()
        if resolved == path or resolved in path.parents or path in resolved.parents:
            raise ValueError("checkpoint cache overlaps source or target")
    cache.mkdir(parents=True, exist_ok=True)


def materialize(backend, name, digest, size, destination, cache):
    """Return transferred bytes; never trust a filename as proof of its contents."""
    if cache is None:
        backend.get(name, destination)
        if digest_file(destination) != (digest, size):
            raise ValueError("checkpoint object failed verification")
        return size
    cached = cache / name
    no_links(cached)
    cached.parent.mkdir(parents=True, exist_ok=True)
    transferred = 0
    if not cached.exists():
        with tempfile.TemporaryDirectory(dir=cached.parent) as temporary:
            staged = Path(temporary) / "object"
            backend.get(name, staged)
            if digest_file(staged) != (digest, size):
                raise ValueError("checkpoint object failed verification")
            with staged.open("r+b") as stream:
                os.fsync(stream.fileno())
            try:
                publish(staged, cached)
            except FileExistsError:
                pass  # A concurrent publisher must have exactly the same bytes.
            transferred = size
    if digest_file(cached) != (digest, size):
        raise ValueError("checkpoint cache object failed verification")
    # Same-volume hard links retain a complete checkpoint with no parent dependency.
    # Cache/checkpoint objects are immutable; restore always copies into fresh state.
    os.link(cached, destination)
    return transferred
