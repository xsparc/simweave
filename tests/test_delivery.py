import importlib.util
import shutil
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.cli import main
from simweave.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_malformed_recording_is_a_cli_error_without_traceback(tmp_path, capsys):
    path = tmp_path / "bad.jsonl"
    path.write_text("[]\n")
    assert main(["replay", str(path)]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_packaged_dashboard_assets_and_browser_security(tmp_path):
    app = create_app(Settings(tmp_path / "db.sqlite3", {"c" * 40: "demo"}))
    with TestClient(app) as client:
        index = client.get("/")
        assert index.status_code == 200
        assert "Run &amp; replay" in index.text or "Run & replay" in index.text
        assert "frame-ancestors 'none'" in index.headers["content-security-policy"]
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/app.css").status_code == 200
        assert client.get("/static/../config.py").status_code == 404


def test_governance_detects_missing_traceability_and_stale_review(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "governance", ROOT / "scripts/check_governance.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    result = module.check(tmp_path, date(2030, 1, 1))
    assert result["status"] == "fail"  # Source/test references do not exist in the copy.
    assert result["warnings"] == ["evidence review overdue"]
    assert module.check(ROOT, date(2026, 10, 13))["status"] == "pass"
