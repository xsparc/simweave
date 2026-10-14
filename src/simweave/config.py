"""Operator-only configuration. No tokens are accepted from scenario documents."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field

from simweave.contracts import Contract


class CatalogPrincipal(Contract):
    tenant: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    subject: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,99}$")
    role: str = Field(pattern=r"^(reader|importer|approver)$")


@dataclass(frozen=True)
class Settings:
    database: Path
    tokens: dict[str, str | dict | CatalogPrincipal]

    def __post_init__(self):
        if not isinstance(self.tokens, dict) or not self.tokens or len(self.tokens) > 100:
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
            return cls(
                Path(os.environ.get("SIMWEAVE_DB", ".simweave/runs.sqlite3")),
                json.loads(os.environ.get("SIMWEAVE_TOKENS", "{}")),
            )
        except (ValueError, TypeError):
            raise ValueError("SIMWEAVE_TOKENS must map secure tokens to tenant names") from None
