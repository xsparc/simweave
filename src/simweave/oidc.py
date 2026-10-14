"""Pinned RFC 9068 resource-server authentication; no discovery from token input."""

import json
import re
import threading
import time
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import jwt

from simweave.config import CatalogPrincipal, OIDCSettings

MAX_TOKEN = 16384
MAX_JWKS = 256 * 1024
REFRESH_COOLDOWN = 5
SCOPES = {"reader": "catalog:read", "importer": "catalog:import", "approver": "catalog:approve"}


class InvalidToken(ValueError):
    pass


class InsufficientScope(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def fetch_keys(uri: str) -> bytes:
    # No token, cookies, credentials or ambient proxy configuration go to this endpoint.
    with build_opener(ProxyHandler({}), NoRedirect).open(
        Request(uri, headers={"Accept": "application/json"}), timeout=5
    ) as response:
        data = response.read(MAX_JWKS + 1)
    if len(data) > MAX_JWKS:
        raise ValueError("JWKS too large")
    return data


class OIDCVerifier:
    def __init__(self, settings: OIDCSettings):
        self.settings = settings
        self._keys = {}
        self._expires = 0.0
        self._attempted = float("-inf")
        self._lock = threading.Lock()

    def _key(self, kid):
        with self._lock:
            now = time.monotonic()
            if now < self._expires and kid in self._keys:
                return self._keys[kid]
            if now - self._attempted < REFRESH_COOLDOWN:
                raise InvalidToken("key refresh cooldown")
            self._attempted = now
            raw = fetch_keys(self.settings.jwks_uri)
            if len(raw) > MAX_JWKS:
                raise InvalidToken("JWKS too large")
            document = json.loads(raw, object_pairs_hook=_unique)
            rows = document.get("keys")
            if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
                raise InvalidToken("invalid JWKS key count")
            keys, seen = {}, set()
            for row in rows:
                if not isinstance(row, dict):
                    raise InvalidToken("invalid JWK")
                identifier = row.get("kid")
                if (
                    not isinstance(identifier, str)
                    or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", identifier)
                    or identifier in seen
                ):
                    raise InvalidToken("invalid or duplicate key identifier")
                seen.add(identifier)
                if (
                    row.get("kty") != "RSA"
                    or row.get("use", "sig") != "sig"
                    or row.get("alg", "RS256") != "RS256"
                ):
                    continue
                if any(field in row for field in ("d", "p", "q", "dp", "dq", "qi")):
                    raise InvalidToken("expected public JWK")
                if len(row.get("n", "")) > 1400 or len(row.get("e", "")) > 8:
                    raise InvalidToken("oversized RSA parameters")
                key = jwt.PyJWK.from_dict(row, algorithm="RS256").key
                if not 2048 <= key.key_size <= 8192:
                    raise InvalidToken("unsupported RSA key size")
                keys[identifier] = key
            if not keys:
                raise InvalidToken("no supported signing keys")
            self._keys, self._expires = keys, time.monotonic() + self.settings.cache_seconds
            if kid not in keys:
                raise InvalidToken("unknown signing key")
            return keys[kid]

    def verify(self, token: str) -> CatalogPrincipal:
        try:
            if not isinstance(token, str) or not token.isascii() or len(token) > MAX_TOKEN:
                raise InvalidToken("invalid token size")
            parts = token.split(".")
            if len(parts) != 3:
                raise InvalidToken("invalid token format")
            header = json.loads(jwt.utils.base64url_decode(parts[0]), object_pairs_hook=_unique)
            # Reject duplicate payload keys before the library verifies the signed bytes.
            json.loads(jwt.utils.base64url_decode(parts[1]), object_pairs_hook=_unique)
            if (
                not isinstance(header, dict)
                or set(header) != {"alg", "typ", "kid"}
                or header["alg"] != "RS256"
                or header["typ"].lower() not in ("at+jwt", "application/at+jwt")
                or not isinstance(header["kid"], str)
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", header["kid"])
            ):
                raise InvalidToken("unsupported access token header")
            claims = jwt.decode(
                token,
                self._key(header["kid"]),
                algorithms=["RS256"],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                leeway=self.settings.clock_skew_seconds,
                options={
                    "require": ["iss", "sub", "aud", "exp", "iat", "jti", "client_id"],
                    "strict_aud": True,
                },
            )
            if (
                any(type(claims.get(field)) is not int for field in ("exp", "iat"))
                or ("nbf" in claims and type(claims["nbf"]) is not int)
                or not 0 < claims["exp"] - claims["iat"] <= self.settings.max_token_seconds
                or claims["client_id"] not in self.settings.client_ids
                or any(
                    not isinstance(claims.get(field), str) or not 1 <= len(claims[field]) <= 200
                    for field in ("sub", "jti", "client_id")
                )
            ):
                raise InvalidToken("invalid access token claims")
            principal = self.settings.principals.get(claims["sub"])
            if principal is None:
                raise InvalidToken("unmapped subject")
            scope = claims.get("scope", "")
            if (
                not isinstance(scope, str)
                or len(scope) > 2048
                or SCOPES[principal.role] not in scope.split()
            ):
                raise InsufficientScope("catalog scope required")
            return principal
        except InsufficientScope:
            raise
        except (
            jwt.PyJWTError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            OSError,
            RecursionError,
        ):
            # Never expose JWT claims, endpoint details, keys or upstream response bodies.
            raise InvalidToken("invalid access token") from None
