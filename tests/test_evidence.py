import base64
import hashlib
import json
import re
import stat
import struct
import subprocess
import zipfile

import pytest

from simweave.bundles import read_bundle
from simweave.cli import main
from simweave.offline import render_report
from simweave.provenance import capture
from simweave.rerun import rerun_container, rerun_here
from simweave.suites import Suite, execute_suite


def suite(**changes):
    return Suite.model_validate(
        {
            "name": "Recovery review",
            "scenarios": [{"name": "Cart"}],
            "seeds": [1],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {"kp": 0.0, "kd": 0.0},
            **changes,
        }
    )


@pytest.fixture
def recorded(tmp_path):
    output = tmp_path / "original"
    report = execute_suite(suite(), output, environment=capture("a" * 40, "sha256:" + "b" * 64))
    return output, report


def rewrite(source, target, modify, extra=None):
    with zipfile.ZipFile(source) as archive:
        data = {name: archive.read(name) for name in archive.namelist()}
    modify(data)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in data.items():
            archive.writestr(name, content)
        if extra:
            archive.writestr(*extra)
    return target


def rehash(data, name):
    manifest = json.loads(data["manifest.json"])
    manifest["files"][name] = {
        "size": len(data[name]),
        "sha256": hashlib.sha256(data[name]).hexdigest(),
    }
    data["manifest.json"] = json.dumps(manifest).encode()


def test_bundle_round_trip_provenance_and_exact_failed_rerun(recorded, tmp_path):
    output, report = recorded
    manifest, restored = read_bundle(output / "evidence.zip")
    assert restored == report
    assert manifest.environment.source_revision == "a" * 40
    assert manifest.environment.image_id == "sha256:" + "b" * 64
    assert manifest.environment.dependencies.pydantic
    assert manifest.environment.dependencies.simweave
    assert not {"hostname", "user", "cwd", "environ"} & manifest.environment.model_dump().keys()
    assert main(["bundle-check", str(output / "evidence.zip")]) == 0
    assert rerun_here(output / "evidence.zip", tmp_path / "rerun") == 0
    verdict = json.loads((tmp_path / "rerun/reproduction.json").read_text())
    assert verdict["status"] == "reproduced"
    assert verdict["original_exit_code"] == verdict["rerun_exit_code"] == 1
    assert all(c["telemetry_matches"] and c["result_matches"] for c in verdict["cases"])
    assert (
        main(["report", str(output / "report.json"), "--output", str(tmp_path / "review.html")])
        == 0
    )
    assert "Unknown: report converted" in (tmp_path / "review.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("kind", ["hash", "telemetry", "preview", "scenario", "extra", "version"])
def test_corruption_rejected_even_with_recomputed_checksums(recorded, tmp_path, kind):
    output, _ = recorded

    def change(data):
        if kind in ("hash", "telemetry"):
            name = "case-0000/telemetry.jsonl"
            lines = data[name].splitlines()
            sample = json.loads(lines[1])
            sample["position"] += 1
            lines[1] = json.dumps(sample).encode()
            data[name] = b"\n".join(lines) + b"\n"
            if kind == "telemetry":
                rehash(data, name)
        elif kind == "preview":
            report = json.loads(data["report.json"])
            report["cases"][0]["summary"]["trajectory"][1]["position"] += 1
            data["report.json"] = json.dumps(report).encode()
            rehash(data, "report.json")
        elif kind == "scenario":
            name = "case-0000/scenario.json"
            scenario = json.loads(data[name])
            scenario["seed"] = 100
            data[name] = json.dumps(scenario).encode()
            rehash(data, name)
        elif kind == "extra":
            data["../escape.py"] = b"do not execute"
            rehash(data, "../escape.py")
        else:
            m = json.loads(data["manifest.json"])
            m["schema_version"] = True
            data["manifest.json"] = json.dumps(m).encode()

    path = rewrite(output / "evidence.zip", tmp_path / "bad.zip", change)
    with pytest.raises(ValueError):
        read_bundle(path)
    assert not (tmp_path / "escape.py").exists()


@pytest.mark.parametrize("name", ["/absolute", "../outside", "C:\\outside", "nested/../../out"])
def test_unknown_and_traversal_members_are_never_extracted(recorded, tmp_path, name):
    output, _ = recorded
    path = rewrite(output / "evidence.zip", tmp_path / "bad.zip", lambda data: None, (name, b"x"))
    with pytest.raises(ValueError):
        read_bundle(path)


def test_duplicate_symlink_compression_and_size_limits(recorded, tmp_path, monkeypatch):
    output, _ = recorded
    with pytest.warns(UserWarning, match="Duplicate"):
        path = rewrite(
            output / "evidence.zip", tmp_path / "dup.zip", lambda d: None, ("report.json", b"{}")
        )
    with pytest.raises(ValueError):
        read_bundle(path)
    link = zipfile.ZipInfo("link")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    path = rewrite(
        output / "evidence.zip", tmp_path / "link.zip", lambda d: None, (link, b"target")
    )
    with pytest.raises(ValueError):
        read_bundle(path)
    monkeypatch.setattr("simweave.bundles.MAX_MEMBER", 100)
    with pytest.raises(ValueError):
        read_bundle(output / "evidence.zip")


def test_oversized_directory_rejected_before_zip_parsing(recorded, tmp_path, monkeypatch):
    output, _ = recorded
    payload = bytearray((output / "evidence.zip").read_bytes())
    struct.pack_into("<HH", payload, len(payload) - 14, 65535, 65535)
    path = tmp_path / "many-entries.zip"
    path.write_bytes(payload)
    monkeypatch.setattr("simweave.bundles.zipfile.ZipFile", lambda *a: pytest.fail("parsed"))
    with pytest.raises(ValueError, match="directory"):
        read_bundle(path)


def test_invalid_archive_cli_has_no_traceback(tmp_path, capsys):
    path = tmp_path / "invalid.zip"
    path.write_bytes(b"not a ZIP")
    assert main(["bundle-check", str(path)]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_report_and_bundle_output_are_not_overwritten(recorded, tmp_path):
    output, _ = recorded
    path = tmp_path / "existing.html"
    path.write_text("keep")
    assert main(["report", str(output / "report.json"), "--output", str(path)]) == 2
    assert path.read_text() == "keep"
    with pytest.raises(FileExistsError):
        execute_suite(suite(), output)


def test_mismatch_prevents_simulation(recorded, tmp_path, monkeypatch):
    output, _ = recorded
    current = capture().model_copy(update={"python": "0.0.0"})
    monkeypatch.setattr("simweave.rerun.capture", lambda *a: current)
    monkeypatch.setattr("simweave.rerun.execute_suite", lambda *a, **k: pytest.fail("executed"))
    assert rerun_here(output / "evidence.zip", tmp_path / "mismatch") == 2
    verdict = json.loads((tmp_path / "mismatch/reproduction.json").read_text())
    assert verdict == {
        "schema_version": 1,
        "status": "environment_mismatch",
        "mismatches": ["python"],
    }
    assert not (tmp_path / "mismatch/report.json").exists()


def test_execution_errors_stay_explicit_and_do_not_claim_reproduction(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ImportError("synthetic private diagnostic")

    monkeypatch.setattr("simweave.suites.execute", unavailable)
    execute_suite(suite(), tmp_path / "errors")
    manifest, report = read_bundle(tmp_path / "errors/evidence.zip")
    assert set(manifest.files) == {"report.json"}
    assert all(c.error == "adapter_unavailable" for c in report.cases)
    assert "synthetic private" not in (tmp_path / "errors/report.html").read_text(encoding="utf-8")
    assert rerun_here(tmp_path / "errors/evidence.zip", tmp_path / "rerun") == 2
    assert json.loads((tmp_path / "rerun/reproduction.json").read_text())["status"] == "incomplete"


def test_host_requires_explicit_matching_digest_before_docker(recorded, tmp_path, monkeypatch):
    output, _ = recorded
    monkeypatch.setattr("simweave.rerun._docker", lambda *a, **k: pytest.fail("docker invoked"))
    for image in ("latest", "sha256:" + "c" * 64, "--privileged"):
        with pytest.raises(ValueError):
            rerun_container(output / "evidence.zip", image, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_container_limits_no_mounts_and_cleanup_on_failure(recorded, tmp_path, monkeypatch):
    output, _ = recorded
    calls = []

    def docker(*args, **kwargs):
        calls.append(args)
        if args[0] == "image":
            return subprocess.CompletedProcess(args, 0, "sha256:" + "b" * 64 + "\n", "")
        if args[0] == "start":
            raise RuntimeError("container operation failed")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("simweave.rerun._docker", docker)
    with pytest.raises(RuntimeError):
        rerun_container(output / "evidence.zip", "sha256:" + "b" * 64, tmp_path / "out")
    create = calls[1]
    assert create[create.index("--pull") + 1] == "never"
    assert create[create.index("--network") + 1] == "none"
    assert create[create.index("--user") + 1] == "10001:10001"
    assert "--privileged" not in create and "--mount" not in create and "-v" not in create
    assert "no-new-privileges" in create and "--pids-limit" in create
    assert calls[-1][:2] == ("rm", "--force")


def test_offline_html_escapes_untrusted_names_and_hashes_actual_assets(tmp_path):
    name = "</script><img src=x onerror=alert(1)>@@SCRIPT@@"
    report = execute_suite(suite(name=name, scenarios=[{"name": name}]), tmp_path / "hostile")
    html = render_report(report)
    assert name not in html
    assert "\\u003c/script>" in html
    assert 'src="http' not in html and 'href="http' not in html
    assert "connect-src 'none'" in html and "'unsafe-inline'" not in html
    assert html.count("</script>") == 2
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[0]
    style = re.findall(r"<style>(.*?)</style>", html, re.S)[0]
    for content in (script, style):
        digest = base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in html
