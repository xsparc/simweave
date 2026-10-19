import json
import os

import pytest
from test_operator_workflows import setup

from simweave import maintenance, recovery
from simweave.cli import main
from simweave.suite_jobs import SuiteJobs, work_once


def fixture(root):
    jobs, artifacts, suite = setup(root)
    for index, tenant in enumerate(("alpha", "beta")):
        jobs.submit(tenant, suite, str(index))
        assert work_once(jobs, artifacts)
    return jobs, artifacts, suite


def test_checkpoint_cli_accepts_cache_and_preserves_manifest_contract(tmp_path, capsys):
    database = tmp_path / "queue"
    config = tmp_path / "backend.json"
    config.write_text(json.dumps({"root": str(tmp_path / "objects")}), encoding="utf-8")
    common = ["operations", "--database", str(database)]
    options = [
        "--backend",
        str(config),
        "--catalogs",
        str(tmp_path / "catalogs"),
        "--object-cache",
        str(tmp_path / "cache"),
    ]
    assert (
        main([*common, "maintenance", "checkpoint", *options, "--output", str(tmp_path / "first")])
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["paused"] and result["transferred_bytes"] == result["reused_objects"] == 0
    assert result["transfer_seconds"] >= 0
    assert main([*common, "checkpoint", *options, "--quiesced", str(tmp_path / "second")]) == 0
    capsys.readouterr()
    assert set(recovery.verify(tmp_path / "second")) == {
        "schema_version",
        "files",
        "jobs",
        "artifacts",
        "references",
    }


def test_reuse_new_objects_and_standalone_restore(tmp_path, monkeypatch):
    jobs, artifacts, suite = fixture(tmp_path)
    cache = tmp_path / "cache"
    first = maintenance.checkpoint(
        jobs, artifacts, tmp_path / "catalogs", tmp_path / "first", object_cache=cache
    )
    assert first["transferred_bytes"] > 0 and first["reused_objects"] == 0
    jobs.gate.set(False)
    jobs.submit("gamma", suite, "new")
    assert work_once(jobs, artifacts)
    calls = []
    original = artifacts.backend.get

    def get(name, target):
        calls.append(name)
        return original(name, target)

    monkeypatch.setattr(artifacts.backend, "get", get)
    second = maintenance.checkpoint(
        jobs, artifacts, tmp_path / "catalogs", tmp_path / "second", object_cache=cache
    )
    assert second["reused_objects"] == 2 and len(calls) == 1
    assert calls[0].startswith("v1/tenant-gamma/")
    assert second["transferred_bytes"] == (cache / calls[0]).stat().st_size
    # Unlinking cache names does not remove a published checkpoint's object bytes.
    for path in cache.rglob("*.zip"):
        path.unlink()
    assert recovery.verify(tmp_path / "first")["references"] == 2
    assert recovery.restore(tmp_path / "second", tmp_path / "restored")["references"] == 3
    assert SuiteJobs(tmp_path / "restored/runs.sqlite3.suites").gate.paused()


@pytest.mark.parametrize("point", ["after-pause", "during-transfer", "before-publication"])
def test_retry_reuses_completed_objects_and_preserves_pause(tmp_path, monkeypatch, point):
    jobs, artifacts, _ = fixture(tmp_path)
    cache, target = tmp_path / "cache", tmp_path / "snapshot"
    calls = 0
    original = artifacts.backend.get

    def get(name, destination):
        nonlocal calls
        calls += 1
        if point == "during-transfer" and calls == 2:
            destination.write_bytes(b"partial")
            raise OSError("synthetic interruption")
        return original(name, destination)

    monkeypatch.setattr(artifacts.backend, "get", get)
    if point == "after-pause":
        original_drain = maintenance.drain

        def drain(*args):
            original_drain(*args)
            raise OSError("synthetic interruption")

        monkeypatch.setattr(maintenance, "drain", drain)
    if point == "before-publication":
        original_verify = recovery.verify

        def verify(*args):
            original_verify(*args)
            raise OSError("synthetic interruption")

        monkeypatch.setattr(recovery, "verify", verify)
    with pytest.raises(OSError, match="synthetic"):
        maintenance.checkpoint(jobs, artifacts, tmp_path / "catalogs", target, object_cache=cache)
    assert jobs.gate.paused() and not target.exists()
    completed = len(list(cache.rglob("*.zip")))
    assert completed == {"after-pause": 0, "during-transfer": 1, "before-publication": 2}[point]
    monkeypatch.undo()
    result = maintenance.checkpoint(
        SuiteJobs(jobs.db.path), artifacts, tmp_path / "catalogs", target, object_cache=cache
    )
    assert result["reused_objects"] == completed
    assert recovery.restore(target, tmp_path / "restored")["references"] == 2


def test_corrupt_cache_is_rejected_without_source_fetch(tmp_path, monkeypatch):
    jobs, artifacts, _ = fixture(tmp_path)
    cache = tmp_path / "cache"
    maintenance.checkpoint(
        jobs, artifacts, tmp_path / "catalogs", tmp_path / "first", object_cache=cache
    )
    next(cache.rglob("*.zip")).write_bytes(b"corrupt")

    def forbidden(*args):
        raise AssertionError("must reject corrupt cache without fetching")

    monkeypatch.setattr(artifacts.backend, "get", forbidden)
    with pytest.raises(ValueError, match="cache object"):
        maintenance.checkpoint(
            jobs, artifacts, tmp_path / "catalogs", tmp_path / "second", object_cache=cache
        )
    assert not (tmp_path / "second").exists() and jobs.gate.paused()
    with pytest.raises(ValueError):
        recovery.verify(tmp_path / "first")  # Hard links share bytes: detect operator mutation.


def test_cache_overlap_and_symlink_rejected(tmp_path):
    jobs, artifacts, _ = fixture(tmp_path)
    for cache in (tmp_path, artifacts.backend.root, tmp_path / "target/cache"):
        with pytest.raises(ValueError, match="overlaps"):
            maintenance.checkpoint(
                jobs, artifacts, tmp_path / "catalogs", tmp_path / "target", object_cache=cache
            )
    link = tmp_path / "link"
    try:
        os.symlink(artifacts.backend.root, link, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="links"):
        maintenance.checkpoint(
            jobs, artifacts, tmp_path / "catalogs", tmp_path / "target", object_cache=link
        )


def test_corrupt_source_never_enters_cache(tmp_path, monkeypatch):
    jobs, artifacts, _ = fixture(tmp_path)
    monkeypatch.setattr(
        artifacts.backend, "get", lambda name, destination: destination.write_bytes(b"bad")
    )
    with pytest.raises(ValueError, match="object failed"):
        maintenance.checkpoint(
            jobs,
            artifacts,
            tmp_path / "catalogs",
            tmp_path / "target",
            object_cache=tmp_path / "cache",
        )
    assert not list((tmp_path / "cache").rglob("*.zip"))
    assert not (tmp_path / "target").exists()
