"""Real Chromium acceptance against an isolated HTTP service and synthetic credentials."""

import argparse
import json
import socket
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from check_connected_operations import contract, headers, settings, token
from playwright.sync_api import expect, sync_playwright

from simweave.api import create_app
from simweave.suite_jobs import work_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    app = create_app(settings(root / "runtime"))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    url = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("local service did not start")
        time.sleep(0.05)
    cases = []
    try:
        with httpx.Client(base_url=url) as client:
            for tenant in ("alpha", "beta"):
                job = app.state.suite_jobs.submit(tenant, contract(0), "baseline")
                assert work_once(app.state.suite_jobs, app.state.artifacts)
                assert (
                    client.post(
                        "/api/v1/catalog/builds/baseline/from-job",
                        headers=headers(tenant, "importer"),
                        json={"job": job["id"], "role": "baseline"},
                    ).status_code
                    == 201
                )
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        headers=headers(tenant, "approver"),
                        json={
                            "build": "baseline",
                            "policy": {
                                "metrics": [{"metric": "rmse", "max_increase": 0.1}],
                                "resamples": 1000,
                            },
                            "expected_generation": 0,
                            "reason": "synthetic browser acceptance",
                        },
                    ).status_code
                    == 201
                )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/static/workspace.html")

            def done(name, tenant):
                expect(page.locator("#status")).to_have_text("Complete.")
                expect(page.locator("#error")).to_be_hidden()
                cases.append(tenant + ": " + name)

            def connect(tenant, role="importer"):
                page.locator("#run-token").fill(token(tenant, "run"))
                page.locator("#catalog-token").fill(token(tenant, role))
                page.get_by_role("button", name="Connect", exact=True).click()
                expect(page.locator("#status")).to_have_text("Connected.")

            for tenant in ("alpha", "beta"):
                connect(tenant)
                assert page.locator("#run-token").input_value() == ""
                assert page.locator("#catalog-token").input_value() == ""
                cases.append(tenant + ": connect and clear credential inputs")
                page.locator("#suite").fill(contract(0).model_dump_json())
                page.locator("#request-key").fill("cancel-me")
                page.get_by_role("button", name="Submit suite", exact=True).click()
                done("submit", tenant)
                identifier = page.locator("#jobs").input_value()
                page.get_by_role("button", name="Submit suite", exact=True).click()
                done("idempotent retry", tenant)
                assert page.locator("#jobs").input_value() == identifier
                page.locator("#inspect-job").click()
                done("inspect queued job", tenant)
                page.locator("#cancel-job").click()
                done("cancel queued job", tenant)
                expect(page.locator("#job-detail")).to_contain_text("cancelled")
                page.locator("#request-key").fill("candidate")
                page.get_by_role("button", name="Submit suite", exact=True).click()
                done("submit candidate", tenant)
                assert work_once(app.state.suite_jobs, app.state.artifacts)
                page.locator("#inspect-job").click()
                done("inspect completed evidence", tenant)
                expect(page.locator("#job-detail")).to_contain_text("succeeded")
                with page.expect_download() as download:
                    page.locator("#download-job").click()
                evidence = root / f"{tenant}-evidence.zip"
                download.value.save_as(evidence)
                assert evidence.read_bytes().startswith(b"PK")
                done("download job", tenant)
                page.locator("#build-label").fill("candidate-" + tenant)
                page.locator("#import-job").click()
                done("import job", tenant)
                page.locator("#builds").select_option("candidate-" + tenant)
                page.locator("#inspect-build").click()
                done("inspect build", tenant)
                expect(page.locator("#build-detail")).to_contain_text("candidate-" + tenant)
                page.locator("#compare").click()
                done("pinned comparison", tenant)
                expect(page.locator("#verdict")).to_contain_text(
                    "inconclusive / baseline generation 1"
                )
                with page.expect_download() as download:
                    page.locator("#download-build").click()
                copy = root / f"{tenant}-build.zip"
                download.value.save_as(copy)
                assert copy.read_bytes() == evidence.read_bytes()
                done("download retained build", tenant)
                page.locator("#build-label").fill("uploaded-" + tenant)
                page.locator("#bundle").set_input_files(evidence)
                page.locator("#upload").click()
                done("upload evidence", tenant)
                page.screenshot(path=str(root / f"{tenant}-workspace.png"), full_page=True)
                connect(tenant, "reader")
                expect(page.locator("#upload")).to_be_disabled()
                expect(page.locator("#import-job")).to_be_disabled()
                expect(page.locator("#compare")).to_be_disabled()
                cases.append(tenant + ": reader role controls")
                page.locator("#disconnect").focus()
                page.keyboard.press("Enter")
                expect(page.locator("#identity")).to_contain_text("Disconnected")
                expect(page.locator("#job-detail")).to_have_text("No job selected.")
                expect(page.locator("#build-detail")).to_have_text("No build selected.")
                cases.append(tenant + ": keyboard disconnect clears evidence")
            assert len(cases) == 30
            # Extra acceptance: invalid credentials, invalid JSON, cross-tenant job import.
            page.locator("#run-token").fill("invalid")
            page.get_by_role("button", name="Connect", exact=True).click()
            expect(page.locator("#error")).to_contain_text("401")
            connect("alpha")
            page.locator("#suite").fill("{invalid")
            page.get_by_role("button", name="Submit suite", exact=True).click()
            expect(page.locator("#error")).to_be_visible()
            page.locator("#run-token").fill(token("beta", "run"))
            page.locator("#catalog-token").fill(token("alpha", "importer"))
            page.get_by_role("button", name="Connect", exact=True).click()
            expect(page.locator("#status")).to_have_text("Connected.")
            beta = next(j for j in app.state.suite_jobs.list("beta") if j["status"] == "succeeded")
            page.locator("#jobs").select_option(beta["id"])
            page.locator("#inspect-job").click()
            expect(page.locator("#status")).to_have_text("Complete.")
            page.locator("#build-label").fill("cross-tenant")
            page.locator("#import-job").click()
            expect(page.locator("#error")).to_contain_text("404")
            page.locator("#disconnect").click()
            # Labeled native controls are reachable without a mouse.
            page.locator("#run-token").focus()
            page.keyboard.press("Tab")
            expect(page.locator("#catalog-token")).to_be_focused()
            connect("alpha")
            pending = []
            page.route("**/api/v1/suite-jobs?*", lambda route: pending.append(route))
            page.locator("#refresh-jobs").click()
            expect(page.locator("#status")).to_have_text("Working...")
            page.locator("#disconnect").click()
            assert pending
            pending[0].fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"items": [{"id": "late-alpha", "status": "succeeded"}]}),
            )
            page.unroute("**/api/v1/suite-jobs?*")
            expect(page.locator("#jobs")).not_to_contain_text("late-alpha")
            expect(page.locator("#identity")).to_contain_text("Disconnected")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(root / "mobile-workspace.png"), full_page=True)
            assert not errors, errors
            browser.close()
        result = {
            "schema_version": 1,
            "browser": "Chromium",
            "tenants": 2,
            "workflow_cases": cases,
            "additional_checks": [
                "invalid credentials",
                "invalid JSON",
                "cross-tenant import denied",
                "keyboard tab order",
                "late response after disconnect",
                "mobile layout has no horizontal overflow",
            ],
            "page_errors": errors,
        }
        (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {"workflow_cases": len(cases), "additional_checks": 6, "page_errors": len(errors)}
            )
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


if __name__ == "__main__":
    main()
