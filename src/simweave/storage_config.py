"""Operator-only artifact backend configuration shared by API and CLI."""

import os
from pathlib import Path

from simweave.artifacts import S3, Filesystem
from simweave.contracts import Contract


class BackendConfig(Contract):
    schema_version: int = 1
    root: str | None = None
    endpoint: str | None = None
    bucket: str | None = None
    region: str = "us-east-1"


def backend(path: Path):
    if path.stat().st_size > 4096:
        raise ValueError("backend configuration exceeds 4 KiB")
    config = BackendConfig.model_validate_json(path.read_bytes())
    if config.schema_version != 1:
        raise ValueError("unsupported backend configuration")
    if config.root and config.endpoint is None and config.bucket is None:
        return Filesystem(Path(config.root))
    if config.root is None and config.endpoint and config.bucket:
        return S3(
            endpoint=config.endpoint,
            bucket=config.bucket,
            region=config.region,
            access_key=os.environ["SIMWEAVE_S3_ACCESS_KEY"],
            secret=os.environ["SIMWEAVE_S3_SECRET_KEY"],
        )
    raise ValueError("configure exactly one storage backend")


def artifact_database(queue: Path):
    return queue.with_name(queue.name + ".artifacts")
