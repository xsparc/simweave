"""Real Keycloak service-account access tokens; no production credentials or login UI."""

import argparse
import json
import time
import uuid
from pathlib import Path

import httpx
import jwt
from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.config import OIDCSettings, Settings
from simweave.suites import Suite, execute_suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:19030")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.url.startswith("http://127.0.0.1:"):
        raise ValueError("drill only accepts an explicit loopback fixture")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    realm = "simweave-fixture-" + uuid.uuid4().hex[:8]
    base = args.url.rstrip("/")
    issuer = base + "/realms/" + realm
    with httpx.Client(timeout=15, trust_env=False) as http:
        admin = http.post(
            base + "/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "grant_type": "password",
                "username": "fixture-admin",
                "password": "synthetic-admin-only",
            },
        )
        admin.raise_for_status()
        auth = {"Authorization": "Bearer " + admin.json()["access_token"]}

        def manage(method, path, body=None):
            response = http.request(method, base + "/admin/realms/" + path, headers=auth, json=body)
            response.raise_for_status()
            return response.json() if response.content else None

        manage(
            "POST",
            "",
            {"realm": realm, "enabled": True, "accessTokenLifespan": 120, "sslRequired": "none"},
        )
        principals = {}
        tokens = {}
        clients = {}
        scopes = {
            "reader": "catalog:read",
            "importer": "catalog:import",
            "approver": "catalog:approve",
        }

        for scope in scopes.values():
            manage(
                "POST",
                realm + "/client-scopes",
                {
                    "name": scope,
                    "protocol": "openid-connect",
                    "attributes": {"include.in.token.scope": "true"},
                },
            )

        def issue(name):
            response = http.post(
                issuer + "/protocol/openid-connect/token",
                data={
                    "client_id": name,
                    "client_secret": "synthetic-client-only",
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            return response.json()

        for tenant in ("alpha", "beta"):
            for role in scopes:
                name = tenant + "-" + role
                manage(
                    "POST",
                    realm + "/clients",
                    {
                        "clientId": name,
                        "enabled": True,
                        "publicClient": False,
                        "secret": "synthetic-client-only",
                        "serviceAccountsEnabled": True,
                        "standardFlowEnabled": False,
                        "directAccessGrantsEnabled": False,
                        "defaultClientScopes": ["basic", scopes[role]],
                        "optionalClientScopes": [],
                        "attributes": {"client_credentials.use_refresh_token": "true"},
                        "protocolMappers": [
                            {
                                "name": "audience",
                                "protocol": "openid-connect",
                                "protocolMapper": "oidc-audience-mapper",
                                "config": {
                                    "included.custom.audience": "simweave-catalog",
                                    "access.token.claim": "true",
                                    "id.token.claim": "false",
                                },
                            },
                        ],
                    },
                )
                client = next(c for c in manage("GET", realm + "/clients") if c["clientId"] == name)
                account = manage(
                    "GET", realm + "/clients/" + client["id"] + "/service-account-user"
                )
                principals[account["id"]] = {"tenant": tenant, "subject": name, "role": role}
                clients[name] = client["id"]
                tokens[name] = issue(name)
        config = OIDCSettings(
            issuer=issuer,
            jwks_uri=issuer + "/protocol/openid-connect/certs",
            audience="simweave-catalog",
            client_ids=list(clients),
            principals=principals,
            token_profile="keycloak",
            allow_insecure_loopback=True,
            clock_skew_seconds=0,
            cache_seconds=5,
        )
        app = create_app(Settings(root / "api.sqlite3", {}, oidc=config))
        suite = Suite.model_validate(
            {
                "name": "provider",
                "scenarios": [
                    {"world": {"steps": 5}, "gates": [{"metric": "rmse", "threshold": 10.0}]}
                ],
                "seeds": [1],
                "adapters": ["reference"],
                "baseline": {},
                "candidate": {},
            }
        )
        execute_suite(suite, root / "suite")
        bundle = (root / "suite/evidence.zip").read_bytes()

        def bearer(name, token=None):
            return {"Authorization": "Bearer " + (token or tokens[name]["access_token"])}

        cases = []
        with TestClient(app) as client:
            for tenant in ("alpha", "beta"):
                for role in scopes:
                    name = tenant + "-" + role
                    response = client.get("/api/v1/catalog", headers=bearer(name))
                    assert response.status_code == 200 and response.json()["role"] == role
                    assert client.get("/api/v1/suite-jobs", headers=bearer(name)).status_code in (
                        401,
                        403,
                    )
                    cases.append(name + " scope and run denial")
                upload = "/api/v1/catalog/builds/" + tenant + "-baseline?role=baseline"
                assert (
                    client.put(
                        upload,
                        content=bundle,
                        headers={**bearer(tenant + "-reader"), "Content-Type": "application/zip"},
                    ).status_code
                    == 403
                )
                assert (
                    client.put(
                        upload,
                        content=bundle,
                        headers={**bearer(tenant + "-importer"), "Content-Type": "application/zip"},
                    ).status_code
                    == 201
                )
                assert (
                    client.get(
                        "/api/v1/catalog/builds/" + tenant + "-baseline",
                        headers=bearer(("beta" if tenant == "alpha" else "alpha") + "-reader"),
                    ).status_code
                    == 404
                )
                promotion = {
                    "build": tenant + "-baseline",
                    "policy": {
                        "metrics": [{"metric": "rmse", "max_increase": 0.1}],
                        "resamples": 1000,
                    },
                    "expected_generation": 0,
                    "reason": "provider fixture",
                }
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        json=promotion,
                        headers=bearer(tenant + "-importer"),
                    ).status_code
                    == 403
                )
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        json=promotion,
                        headers=bearer(tenant + "-approver"),
                    ).status_code
                    == 201
                )
                cases.append(tenant + " import approval and cross-tenant isolation")
            old = tokens["alpha-reader"]["access_token"]
            realm_id = manage("GET", realm)["id"]
            manage(
                "POST",
                realm + "/components",
                {
                    "name": "rotated-rsa",
                    "parentId": realm_id,
                    "providerId": "rsa-generated",
                    "providerType": "org.keycloak.keys.KeyProvider",
                    "config": {
                        "priority": ["200"],
                        "enabled": ["true"],
                        "active": ["true"],
                        "keySize": ["2048"],
                        "algorithm": ["RS256"],
                    },
                },
            )
            rotated = issue("alpha-reader")["access_token"]
            assert (
                jwt.get_unverified_header(old)["kid"] != jwt.get_unverified_header(rotated)["kid"]
            )
            time.sleep(5.1)
            assert (
                client.get("/api/v1/catalog", headers=bearer("alpha-reader", rotated)).status_code
                == 200
            )
            assert (
                client.get("/api/v1/catalog", headers=bearer("alpha-reader", old)).status_code
                == 200
            )
            cases.append("signing-key rotation with retained previous public key")
            revocation = []
            for action in ("revoke", "logout"):
                session = issue("alpha-reader")
                assert "refresh_token" in session
                data = (
                    {
                        "client_id": "alpha-reader",
                        "client_secret": "synthetic-client-only",
                        "refresh_token": session["refresh_token"],
                    }
                    if action == "logout"
                    else {
                        "client_id": "alpha-reader",
                        "client_secret": "synthetic-client-only",
                        "token": session["refresh_token"],
                        "token_type_hint": "refresh_token",
                    }
                )
                response = http.post(issuer + "/protocol/openid-connect/" + action, data=data)
                response.raise_for_status()
                inspection = http.post(
                    issuer + "/protocol/openid-connect/token/introspect",
                    data={
                        "client_id": "alpha-reader",
                        "client_secret": "synthetic-client-only",
                        "token": session["access_token"],
                    },
                )
                inspection.raise_for_status()
                active = inspection.json()["active"]
                offline = client.get(
                    "/api/v1/catalog", headers=bearer("alpha-reader", session["access_token"])
                ).status_code
                assert active is False and offline == 200
                revocation.append(
                    {"action": action, "provider_active": active, "offline_status": offline}
                )
            manage("PUT", realm, {"accessTokenLifespan": 2})
            short = issue("alpha-reader")["access_token"]
            time.sleep(3)
            assert (
                client.get("/api/v1/catalog", headers=bearer("alpha-reader", short)).status_code
                == 401
            )
            cases.append("actual expired access token rejected")
        result = {
            "schema_version": 1,
            "provider": "Keycloak 26.4.7",
            "tenants": 2,
            "roles": 3,
            "cases": cases,
            "revocation": revocation,
            "limitation": (
                "offline JWTs remain valid after provider revocation/logout until expiry; "
                "no browser login flow tested"
            ),
        }
        (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
