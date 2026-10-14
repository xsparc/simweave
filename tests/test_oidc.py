import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from simweave import oidc
from simweave.api import create_app
from simweave.config import OIDCSettings, Settings


@pytest.fixture(scope="module")
def keys():
    return [rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(3)]


def jwk(key, kid="key-1"):
    return {
        **jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True),
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
    }


def config(**changes):
    return OIDCSettings.model_validate(
        {
            "issuer": "https://issuer.example",
            "jwks_uri": "https://issuer.example/keys",
            "audience": "simweave-catalog",
            "client_ids": ["test-client"],
            "principals": {
                f"{tenant}-{role}": {"tenant": tenant, "subject": f"{tenant}.{role}", "role": role}
                for tenant in ("alpha", "beta")
                for role in ("reader", "importer", "approver")
            },
            "clock_skew_seconds": 0,
            **changes,
        }
    )


def token(
    key, *, subject="alpha-reader", scope="catalog:read", kid="key-1", headers=None, **claims
):
    now = int(time.time())
    payload = {
        "iss": "https://issuer.example",
        "aud": "simweave-catalog",
        "sub": subject,
        "iat": now - 1,
        "exp": now + 300,
        "jti": "unique-test-id",
        "client_id": "test-client",
        "scope": scope,
        **claims,
    }
    return jwt.encode(
        payload, key, algorithm="RS256", headers={"kid": kid, "typ": "at+jwt", **(headers or {})}
    )


@pytest.fixture
def verifier(keys, monkeypatch):
    calls = []

    def fetch(uri):
        calls.append(uri)
        return json.dumps({"keys": [jwk(keys[0])]}).encode()

    monkeypatch.setattr(oidc, "fetch_keys", fetch)
    return oidc.OIDCVerifier(config()), calls


def test_signed_token_cache_and_singleflight(verifier, keys):
    check, calls = verifier
    signed = token(keys[0])
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check.verify, [signed] * 20))
    assert {p.tenant for p in results} == {"alpha"}
    assert len(calls) == 1


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://wrong.example"},
        {"aud": "another-api"},
        {"aud": ["simweave-catalog"]},
        {"exp": 1},
        {"iat": 9999999999},
        {"nbf": 9999999999},
        {"iat": True},
        {"exp": "9999999999"},
        {"iat": 1, "exp": 9999999999},
        {"client_id": "unapproved-client"},
        {"sub": "unmapped"},
        {"jti": ""},
        {"jti": None},
        {"nbf": "1"},
    ],
)
def test_invalid_claims_fail_closed(verifier, keys, claims):
    with pytest.raises(oidc.InvalidToken):
        verifier[0].verify(token(keys[0], **claims))


@pytest.mark.parametrize(
    "headers",
    [
        {"typ": "JWT"},
        {"typ": 1},
        {"kid": "../keys"},
        {"jku": "https://attacker.example/keys"},
        {"crit": ["custom"]},
    ],
)
def test_untrusted_headers_never_fetch(verifier, keys, headers):
    with pytest.raises(oidc.InvalidToken):
        verifier[0].verify(token(keys[0], headers=headers))
    assert verifier[1] == []


def test_wrong_signature_unknown_key_unsigned_and_hmac(verifier, keys):
    check, calls = verifier
    with pytest.raises(oidc.InvalidToken):
        check.verify(token(keys[1]))
    for _ in range(10):
        with pytest.raises(oidc.InvalidToken):
            check.verify(token(keys[1], kid="unknown"))
    assert len(calls) == 1
    for algorithm in ("none", "HS256"):
        signed = jwt.encode(
            {"sub": "alpha-reader"},
            "s" * 32 if algorithm == "HS256" else "",
            algorithm=algorithm,
            headers={"typ": "at+jwt", "kid": "key-1"},
        )
        with pytest.raises(oidc.InvalidToken):
            check.verify(signed)
    with pytest.raises(oidc.InvalidToken):
        check.verify("a" * (oidc.MAX_TOKEN + 1))


@pytest.mark.parametrize("scope", ["", "catalog:approve", ["catalog:read"], "x" * 2049])
def test_missing_scope(verifier, keys, scope):
    with pytest.raises(oidc.InsufficientScope):
        verifier[0].verify(token(keys[0], scope=scope))


def test_live_jwks_rotation_removal_failure_and_redirect(keys):
    state = {"body": json.dumps({"keys": [jwk(keys[0])]}).encode(), "status": 200, "calls": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["calls"] += 1
            assert self.headers.get("Authorization") is None
            self.send_response(state["status"])
            if state["status"] == 302:
                self.send_header("Location", "/redirected")
            self.end_headers()
            self.wfile.write(state["body"])

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        uri = f"http://127.0.0.1:{server.server_port}/keys"
        check = oidc.OIDCVerifier(config(jwks_uri=uri, allow_insecure_loopback=True))
        assert check.verify(token(keys[0])).tenant == "alpha"
        state["body"] = json.dumps({"keys": [jwk(keys[1], "key-2")]}).encode()
        check._attempted = float("-inf")
        assert check.verify(token(keys[1], kid="key-2")).tenant == "alpha"
        with pytest.raises(oidc.InvalidToken):
            check.verify(token(keys[0]))
        state["status"] = 503
        check._expires, check._attempted = 0, float("-inf")
        with pytest.raises(oidc.InvalidToken):
            check.verify(token(keys[1], kid="key-2"))
        calls = state["calls"]
        state["status"] = 302
        check._attempted = float("-inf")
        with pytest.raises(oidc.InvalidToken):
            check.verify(token(keys[1], kid="key-2"))
        assert state["calls"] == calls + 1  # No redirect was followed.
        state["status"], state["body"] = 200, b"x" * (oidc.MAX_JWKS + 1)
        check._attempted = float("-inf")
        with pytest.raises(oidc.InvalidToken):
            check.verify(token(keys[1], kid="key-2"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "kind", ["duplicate", "empty", "many", "private", "weak", "huge", "nonobject"]
)
def test_jwks_rejections(keys, monkeypatch, kind):
    public = jwk(keys[0])
    rows = [public]
    if kind == "duplicate":
        rows *= 2
    elif kind == "empty":
        rows = []
    elif kind == "many":
        rows *= 33
    elif kind == "private":
        rows = [{**public, "d": "private"}]
    elif kind == "weak":
        rows = [jwk(rsa.generate_private_key(public_exponent=65537, key_size=1024))]
    elif kind == "huge":
        rows = [{**public, "n": "A" * 1401}]
    elif kind == "nonobject":
        rows = [1]
    monkeypatch.setattr(oidc, "fetch_keys", lambda _: json.dumps({"keys": rows}).encode())
    with pytest.raises(oidc.InvalidToken):
        oidc.OIDCVerifier(config()).verify(token(keys[0]))


def test_two_tenant_role_mapping_and_identity_spoofing(verifier, keys, tmp_path):
    client = TestClient(create_app(Settings(tmp_path / "runs.db", {}, config())))
    for tenant in ("alpha", "beta"):
        for role, scope in oidc.SCOPES.items():
            headers = {
                "Authorization": "Bearer "
                + token(
                    keys[0],
                    subject=f"{tenant}-{role}",
                    scope=scope,
                    tenant="attacker",
                    role="approver",
                    approved_by="spoof",
                )
            }
            response = client.get("/api/v1/catalog", headers=headers)
            assert response.status_code == 200
            assert response.json()["subject"] == f"{tenant}.{role}"
            assert response.json()["role"] == role
            assert client.get("/api/v1/catalog/builds/foreign", headers=headers).status_code == 404
            assert client.get("/api/v1/runs", headers=headers).status_code == 401
            body = {"to_generation": 1, "expected_generation": 0, "reason": "test"}
            assert client.post(
                "/api/v1/catalog/rollback", headers=headers, json=body
            ).status_code == (409 if role == "approver" else 403)
    header = {"Authorization": "Bearer " + token(keys[0], scope="catalog:approve")}
    assert client.get("/api/v1/catalog", headers=header).status_code == 403
    expired = {"Authorization": "Bearer " + token(keys[0], exp=1)}
    response = client.get("/api/v1/catalog", headers=expired)
    assert response.status_code == 401
    assert 'error="invalid_token"' in response.headers["www-authenticate"]


@pytest.mark.parametrize(
    "change",
    [
        {"issuer": "http://example.com"},
        {"jwks_uri": "http://127.0.0.1/keys"},
        {"jwks_uri": "https://user:password@example.com/keys"},
        {"jwks_uri": "file:///keys"},
        {"issuer": "https://example.com?x=1"},
        {"client_ids": []},
        {"principals": {}},
    ],
)
def test_operator_configuration_bounds(change):
    with pytest.raises(ValueError):
        config(**change)


@pytest.mark.parametrize("missing", ["iss", "aud", "sub", "exp", "iat", "jti", "client_id"])
def test_required_claims(verifier, keys, missing):
    claims = jwt.decode(token(keys[0]), options={"verify_signature": False})
    del claims[missing]
    signed = jwt.encode(
        claims, keys[0], algorithm="RS256", headers={"typ": "at+jwt", "kid": "key-1"}
    )
    with pytest.raises(oidc.InvalidToken):
        verifier[0].verify(signed)


def test_oidc_import_approval_and_tenant_isolation(verifier, keys, tmp_path, monkeypatch):
    import tempfile

    from simweave.suites import Suite, execute_suite

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    suite = Suite.model_validate(
        {
            "name": "OIDC verification",
            "scenarios": [
                {
                    "name": "Cart",
                    "world": {"steps": 5},
                    "gates": [{"metric": "rmse", "threshold": 10.0}],
                }
            ],
            "seeds": [1],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )
    output = tmp_path / "suite"
    execute_suite(suite, output)
    client = TestClient(create_app(Settings(tmp_path / "runs.db", {}, config())))

    def headers(tenant, role):
        return {
            "Authorization": "Bearer "
            + token(keys[0], subject=f"{tenant}-{role}", scope=oidc.SCOPES[role])
        }

    response = client.put(
        "/api/v1/catalog/builds/build-1",
        headers={**headers("alpha", "importer"), "Content-Type": "application/zip"},
        content=(output / "evidence.zip").read_bytes(),
    )
    assert response.status_code == 201
    body = {
        "build": "build-1",
        "expected_generation": 0,
        "reason": "Verified OIDC identity",
        "policy": {"metrics": [{"metric": "rmse", "max_increase": 0.02}]},
    }
    assert (
        client.post(
            "/api/v1/catalog/promote", headers=headers("beta", "approver"), json=body
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/catalog/promote", headers=headers("alpha", "importer"), json=body
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/catalog/promote", headers=headers("alpha", "approver"), json=body
    )
    assert response.status_code == 201
    assert response.json()["approval"]["approved_by"] == "alpha.approver"
    assert (
        client.get("/api/v1/catalog/events", headers=headers("beta", "reader")).json()["items"]
        == []
    )
