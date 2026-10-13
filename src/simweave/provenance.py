"""Small, explicit runtime fingerprints; never collect machine identity or environment dumps."""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
from pathlib import Path
from typing import Annotated

from pydantic import Field

from simweave.contracts import Contract

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Revision = Annotated[str, Field(pattern=r"^[a-f0-9]{40}$")]
ImageID = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
Version = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._+!-]+$")]


class Dependencies(Contract):
    simweave: Version | None
    pydantic: Version | None
    pydantic_core: Version | None
    numpy: Version | None
    mujoco: Version | None


class Environment(Contract):
    python: Version
    system: Version
    architecture: Version
    implementation_digest: Digest
    dependencies: Dependencies
    source_revision: Revision | None = None
    image_id: ImageID | None = None


def capture(source_revision: str | None = None, image_id: str | None = None) -> Environment:
    digest = hashlib.sha256()
    root = Path(__file__).parent
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    versions = {}
    for name in Dependencies.model_fields:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return Environment(
        python=platform.python_version(),
        system=platform.system(),
        architecture=platform.machine(),
        implementation_digest=digest.hexdigest(),
        dependencies=Dependencies.model_validate(versions),
        source_revision=source_revision,
        image_id=image_id,
    )


def mismatches(recorded: Environment, current: Environment) -> list[str]:
    # Revision/image labels are operator assertions. The host verifies image identity;
    # the child compares actual installed code and versions, not copied labels.
    keys = ("python", "system", "architecture", "implementation_digest", "dependencies")
    return [key for key in keys if getattr(recorded, key) != getattr(current, key)]
