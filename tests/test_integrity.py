import hashlib
import json

import pytest

from simweave.artifacts import Artifacts, Filesystem, key
from simweave.cli import main
from simweave.integrity import audit
from simweave.storage_config import artifact_database


def retained(root, count=5):
    storage = Artifacts(artifact_database(root / "queue"), Filesystem(root / "objects"))
    digests = []
    for i in range(count):
        data = f"synthetic bytes {i}".encode()
        digest = hashlib.sha256(data).hexdigest()
        for tenant in ("alpha", "beta"):
            target = storage.backend.root / key(tenant, digest)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            storage.retain(tenant, digest, len(data))
        digests.append(digest)
    return storage, sorted(digests)


def test_pages_cover_only_selected_tenant_without_mutating_index(tmp_path):
    storage, digests = retained(tmp_path)
    with storage.db.connect() as db:
        before = list(db.execute("SELECT * FROM artifacts ORDER BY tenant,digest"))
    first = audit(storage, "alpha", limit=2)
    second = audit(storage, "alpha", after=first["next_after"], limit=2)
    last = audit(storage, "alpha", after=second["next_after"], limit=2)
    assert first["healthy"] and second["healthy"] and last["healthy"]
    assert last["next_after"] is None
    assert [item["digest"] for page in (first, second, last) for item in page["results"]] == digests
    assert audit(storage, "unknown")["checked"] == 0
    with storage.db.connect() as db:
        assert list(db.execute("SELECT * FROM artifacts ORDER BY tenant,digest")) == before
    assert len(list(storage.backend.root.rglob("*.zip"))) == 10


def test_corrupt_missing_unavailable_are_reported_and_cursor_advances(tmp_path, monkeypatch):
    storage, digests = retained(tmp_path)
    (storage.backend.root / key("alpha", digests[0])).write_bytes(b"bad")
    (storage.backend.root / key("alpha", digests[1])).unlink()
    original = storage.backend.get
    calls = []

    def get(name, target):
        calls.append(name)
        if digests[2] in name:
            raise RuntimeError("private provider diagnostic must not escape")
        return original(name, target)

    monkeypatch.setattr(storage.backend, "get", get)
    result = audit(storage, "alpha", limit=3)
    assert [row["status"] for row in result["results"]] == ["corrupt", "missing", "unavailable"]
    assert result["counts"] == {"verified": 0, "corrupt": 1, "missing": 1, "unavailable": 1}
    assert not result["healthy"] and result["next_after"] == digests[2]
    assert all(name.startswith("v1/tenant-alpha/") for name in calls)
    assert "private" not in json.dumps(result)
    assert audit(storage, "alpha", after=result["next_after"])["counts"]["verified"] == 2
    # Failures are observation only, never repair/delete or alter the other tenant.
    monkeypatch.setattr(storage.backend, "get", original)
    assert audit(storage, "beta")["counts"]["verified"] == 5
    assert not (storage.backend.root / key("alpha", digests[1])).exists()


@pytest.mark.parametrize(
    "options", [{"limit": 0}, {"limit": 26}, {"limit": True}, {"after": "../x"}, {"after": 3}]
)
def test_invalid_bounds_fail_before_io(tmp_path, monkeypatch, options):
    storage, _ = retained(tmp_path)
    monkeypatch.setattr(storage.backend, "get", lambda *args: pytest.fail("unexpected object read"))
    with pytest.raises(ValueError):
        audit(storage, "alpha", **options)


def test_corrupt_metadata_fails_before_object_reads(tmp_path, monkeypatch):
    storage, _ = retained(tmp_path)
    with storage.db.connect() as db:
        db.execute("UPDATE artifacts SET size=-1 WHERE tenant='alpha'")
    monkeypatch.setattr(storage.backend, "get", lambda *args: pytest.fail("unexpected object read"))
    with pytest.raises(ValueError, match="metadata"):
        audit(storage, "alpha")


def test_cli_json_exit_codes_and_resume(tmp_path, capsys):
    storage, digests = retained(tmp_path)
    config = tmp_path / "backend.json"
    config.write_text(json.dumps({"root": str(storage.backend.root)}), encoding="utf-8")
    command = [
        "operations",
        "--database",
        str(tmp_path / "queue"),
        "audit",
        "--backend",
        str(config),
        "--tenant",
        "alpha",
        "--limit",
        "2",
    ]
    assert main(command) == 0
    page = json.loads(capsys.readouterr().out)
    assert page["next_after"] == digests[1]
    (storage.backend.root / key("alpha", digests[2])).unlink()
    assert main([*command, "--after", page["next_after"]]) == 1
    assert json.loads(capsys.readouterr().out)["counts"]["missing"] == 1
    assert main([*command, "--limit", "26"]) == 2
    assert "Operation failed" in capsys.readouterr().err


def test_unavailable_scratch_is_not_reported_as_missing_evidence(tmp_path):
    storage, _ = retained(tmp_path, count=1)
    storage.scratch = tmp_path / "absent-scratch"
    result = audit(storage, "alpha")
    assert result["counts"]["unavailable"] == 1
    assert result["counts"]["missing"] == 0


def test_invalid_digest_type_fails_as_metadata_error(tmp_path):
    storage, _ = retained(tmp_path, count=1)
    with storage.db.connect() as db:
        db.execute("UPDATE artifacts SET digest=? WHERE tenant='alpha'", (b"not-text",))
    with pytest.raises(ValueError, match="metadata"):
        audit(storage, "alpha")
