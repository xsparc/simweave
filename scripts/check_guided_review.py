"""Twenty guided approval cases against a real local API and 30-pair evidence."""

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
    root = parser.parse_args().output.resolve()
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
            raise RuntimeError("test service did not start")
        time.sleep(0.05)
    cases, errors = [], []
    policy = {"metrics": [{"metric": "rmse", "max_increase": 0.1}], "resamples": 1000}
    try:
        with httpx.Client(base_url=url, timeout=60) as client, sync_playwright() as pw:
            for tenant in ("alpha", "beta"):
                suite = contract(0).model_dump()
                suite["seeds"] = list(range(30))
                suite["scenarios"][0]["sensors"] = {"position_noise_std": 0.03}
                suite["candidate"] = {"kp": 8.1, "kd": 4.0}
                from simweave.suites import Suite

                job = app.state.suite_jobs.submit(tenant, Suite.model_validate(suite), "review")
                assert work_once(app.state.suite_jobs, app.state.artifacts)
                for label, role in (
                    ("baseline-" + tenant, "baseline"),
                    ("candidate-" + tenant, "candidate"),
                ):
                    assert (
                        client.post(
                            f"/api/v1/catalog/builds/{label}/from-job",
                            headers=headers(tenant, "importer"),
                            json={"job": job["id"], "role": role},
                        ).status_code
                        == 201
                    )
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/static/workspace.html")

            def connect(tenant, role):
                page.locator("#catalog-token").fill(token(tenant, role))
                page.get_by_role("button", name="Connect", exact=True).click()
                expect(page.locator("#status")).to_have_text("Connected.")

            def done():
                expect(page.locator("#status")).to_have_text("Complete.")
                expect(page.locator("#error")).to_be_hidden()

            def open_promotion(tenant):
                page.locator("#builds").select_option("baseline-" + tenant)
                page.locator("#policy").fill(json.dumps(policy))
                page.locator("#approval-reason").fill("Synthetic approval review")
                page.locator("#promote").click()
                expect(page.locator("#approval-dialog")).to_be_visible()
                expect(page.locator("#cancel-approval")).to_be_focused()

            for tenant in ("alpha", "beta"):
                other = "beta" if tenant == "alpha" else "alpha"
                for role in ("reader", "importer"):
                    connect(tenant, role)
                    page.locator("#builds").select_option("baseline-" + tenant)
                    expect(page.locator("#promote")).to_be_disabled()
                    expect(page.locator("#rollback")).to_be_disabled()
                    assert (
                        client.post(
                            "/api/v1/catalog/promote",
                            headers=headers(tenant, role),
                            json={
                                "build": "baseline-" + tenant,
                                "policy": policy,
                                "expected_generation": 0,
                                "reason": "denied",
                            },
                        ).status_code
                        == 403
                    )
                    cases.append(f"{tenant}: {role} cannot approve")
                connect(tenant, "approver")
                expect(page.locator("#builds")).not_to_contain_text("baseline-" + other)
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        headers=headers(tenant, "approver"),
                        json={
                            "build": "baseline-" + other,
                            "policy": policy,
                            "expected_generation": 0,
                            "reason": "denied",
                        },
                    ).status_code
                    == 404
                )
                cases.append(f"{tenant}: cross-tenant build denied")
                open_promotion(tenant)
                page.keyboard.press("Escape")
                expect(page.locator("#approval-dialog")).to_be_hidden()
                assert (
                    client.get("/api/v1/catalog", headers=headers(tenant, "reader")).json()[
                        "generation"
                    ]
                    == 0
                )
                cases.append(f"{tenant}: keyboard cancellation writes nothing")
                open_promotion(tenant)
                page.keyboard.press("Tab")
                expect(page.locator("#confirm-approval")).to_be_focused()
                page.keyboard.press("Enter")
                done()
                expect(page.locator("#baseline")).to_contain_text("generation 1")
                cases.append(f"{tenant}: keyboard promotion from generation zero")
                open_promotion(tenant)
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        headers=headers(tenant, "approver"),
                        json={
                            "build": "candidate-" + tenant,
                            "policy": policy,
                            "expected_generation": 1,
                            "reason": "Concurrent reviewer",
                        },
                    ).status_code
                    == 201
                )
                page.locator("#confirm-approval").click()
                expect(page.locator("#error")).to_contain_text("generation may have changed")
                expect(page.locator("#promote")).to_be_disabled()
                assert (
                    client.get("/api/v1/catalog", headers=headers(tenant, "reader")).json()[
                        "generation"
                    ]
                    == 2
                )
                cases.append(f"{tenant}: stale generation rejected without retry")
                page.locator("#refresh-builds").click()
                done()
                page.locator("#refresh-events").click()
                done()
                page.locator("#events").select_option("1")
                page.locator("#approval-reason").fill("Restore first approval")
                page.locator("#rollback").click()
                expect(page.locator("#approval-preview")).to_contain_text("restored_policy")
                page.locator("#confirm-approval").click()
                done()
                expect(page.locator("#baseline")).to_contain_text("generation 3")
                events = client.get(
                    "/api/v1/catalog/events", headers=headers(tenant, "reader")
                ).json()["items"]
                assert [e["generation"] for e in events] == [1, 2, 3]
                assert events[2]["policy"] == events[0]["policy"]
                assert events[2]["approval"]["approved_by"] == "approver"
                cases.append(f"{tenant}: rollback appends exact policy and identity")
                response = client.post(
                    "/api/v1/catalog/comparisons",
                    headers=headers(tenant, "importer"),
                    json={"build": "candidate-" + tenant, "generation": 3},
                )
                assert response.status_code == 201
                assert response.json()["statistics"]["groups"][0]["complete_pairs"] == 30
                page.locator("#refresh-decisions").click()
                done()
                page.locator("#decisions").select_option("1")
                page.locator("#inspect-decision").click()
                done()
                expect(page.locator("#metric-summary")).to_contain_text("30 complete pairs")
                expect(page.locator("#metric-summary th")).to_have_count(5)
                cases.append(f"{tenant}: approver reads 30-pair metric summary")
                open_promotion(tenant)
                page.locator("#cancel-approval").click()
                page.locator("#disconnect").click()
                expect(page.locator("#metric-summary")).to_be_empty()
                expect(page.locator("#approval-preview")).to_be_empty()
                expect(page.locator("#event-detail")).to_have_text("No approval selected.")
                cases.append(f"{tenant}: disconnect clears review evidence")
                connect(tenant, "reader")
                page.locator("#refresh-events").click()
                done()
                page.locator("#events").select_option("3")
                expect(page.locator("#event-detail")).to_contain_text("Restore first approval")
                expect(page.locator("#rollback")).to_be_disabled()
                cases.append(f"{tenant}: reader inspects immutable history")
            assert len(cases) == 20
            connect("alpha", "approver")
            open_promotion("alpha")
            pending = []
            page.route("**/api/v1/catalog/promote", lambda route: pending.append(route))
            page.locator("#confirm-approval").click()
            expect(page.locator("#status")).to_have_text("Working...")
            page.locator("#disconnect").click()
            assert pending
            pending[0].fulfill(status=201, content_type="application/json", body='{"generation":4}')
            page.unroute("**/api/v1/catalog/promote")
            expect(page.locator("#baseline")).to_have_text("No catalog connected.")
            expect(page.locator("#event-detail")).to_have_text("No approval selected.")
            expect(page.locator("#identity")).to_contain_text("Disconnected")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(root / "guided-review.png"), full_page=True)
            assert not errors
            browser.close()
        (root / "verification.json").write_text(
            json.dumps(
                {
                    "cases": cases,
                    "page_errors": errors,
                    "paired_seeds": 30,
                    "additional_checks": ["late approval response", "mobile overflow"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(json.dumps({"cases": len(cases), "page_errors": len(errors), "paired_seeds": 30}))
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


if __name__ == "__main__":
    main()
