"""Operator-only configuration. No tokens are accepted from scenario documents."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database: Path
    tokens: dict[str, str]

    def __post_init__(self):
        if not isinstance(self.tokens, dict) or not self.tokens or len(self.tokens) > 100:
            raise ValueError("configure between 1 and 100 API tokens")
        for token, tenant in self.tokens.items():
            if (
                not isinstance(token, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token)
                or not isinstance(tenant, str)
                or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", tenant)
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
