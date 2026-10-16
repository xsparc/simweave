"""Operator-only configuration. No tokens are accepted from scenario documents."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from simweave.contracts import Contract


class CatalogPrincipal(Contract):
    tenant: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    subject: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,99}$")
    role: str = Field(pattern=r"^(reader|importer|approver)$")


Subject = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[\x21-\x7e]+$")]


class OIDCSettings(Contract):
    token_profile: Literal["rfc9068", "keycloak"] = "rfc9068"
    issuer: str = Field(min_length=1, max_length=2048)
    jwks_uri: str = Field(min_length=1, max_length=2048)
    audience: str = Field(min_length=1, max_length=200)
    client_ids: list[Subject] = Field(min_length=1, max_length=20)
    principals: dict[Subject, CatalogPrincipal] = Field(min_length=1, max_length=100)
    cache_seconds: int = Field(default=300, ge=5, le=3600)
    max_token_seconds: int = Field(default=900, ge=60, le=3600)
    clock_skew_seconds: int = Field(default=30, ge=0, le=30)
    allow_insecure_loopback: bool = False

    @model_validator(mode="after")
    def secure_endpoints(self):
        for value in (self.issuer, self.jwks_uri):
            url = urlsplit(value)
            loopback = self.allow_insecure_loopback and url.hostname in ("127.0.0.1", "::1")
            if (
                not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or (url.scheme != "https" and not (loopback and url.scheme == "http"))
            ):
                raise ValueError("OIDC endpoints require HTTPS or explicitly enabled loopback")
        return self


@dataclass(frozen=True)
class Settings:
    database: Path
    tokens: dict[str, str | dict | CatalogPrincipal]
    oidc: OIDCSettings | None = None
    artifact_backend: Path | None = None
    postgres: bool = False

    def __post_init__(self):
        if isinstance(self.oidc, dict):
            object.__setattr__(self, "oidc", OIDCSettings.model_validate(self.oidc))
        if self.oidc is not None and not isinstance(self.oidc, OIDCSettings):
            raise ValueError("invalid OIDC configuration")
        if (
            not isinstance(self.tokens, dict)
            or (not self.tokens and self.oidc is None)
            or len(self.tokens) > 100
        ):
            raise ValueError("configure between 1 and 100 API tokens")
        for token, tenant in self.tokens.items():
            if isinstance(tenant, dict):
                tenant = CatalogPrincipal.model_validate(tenant)
                self.tokens[token] = tenant
            name = tenant.tenant if isinstance(tenant, CatalogPrincipal) else tenant
            if (
                not isinstance(token, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token)
                or not isinstance(name, str)
                or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name)
            ):
                raise ValueError("invalid token or tenant configuration")

    @classmethod
    def from_env(cls):
        try:
            if os.environ.get("SIMWEAVE_SUITE_BACKEND", "sqlite") not in ("sqlite", "postgres"):
                raise ValueError("invalid suite backend")
            return cls(
                Path(os.environ.get("SIMWEAVE_DB", ".simweave/runs.sqlite3")),
                json.loads(os.environ.get("SIMWEAVE_TOKENS", "{}")),
                OIDCSettings.model_validate_json(os.environ["SIMWEAVE_OIDC"])
                if os.environ.get("SIMWEAVE_OIDC")
                else None,
                Path(os.environ["SIMWEAVE_ARTIFACT_BACKEND"])
                if os.environ.get("SIMWEAVE_ARTIFACT_BACKEND")
                else None,
                os.environ.get("SIMWEAVE_SUITE_BACKEND", "sqlite") == "postgres",
            )
        except (ValueError, TypeError):
            raise ValueError("invalid SIMWEAVE_TOKENS or SIMWEAVE_OIDC configuration") from None
