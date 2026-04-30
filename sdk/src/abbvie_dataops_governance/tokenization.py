"""Tokenization & sensitive-data policy review (static check; runtime enforcement is per-adapter)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

import yaml

Classification = Literal["public", "internal", "confidential", "restricted"]
Method = Literal["dynamic_mask", "external_token_vault", "hash_salt", "synthetic", "none"]


@dataclass(frozen=True)
class TokenizationPolicy:
    column: str
    classification: Classification
    method: Method
    notes: str = ""


@dataclass
class TokenizationReview:
    policy: TokenizationPolicy
    compliant: bool
    detail: str


def load_policies(path: str | Path) -> list[TokenizationPolicy]:
    p = Path(path)
    payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    items = payload.get("policies", payload if isinstance(payload, list) else [])
    return [
        TokenizationPolicy(
            column=item["column"],
            classification=item["classification"],
            method=item["method"],
            notes=item.get("notes", ""),
        )
        for item in items
    ]


def review_policies(policies: Iterable[TokenizationPolicy]) -> list[TokenizationReview]:
    """Static review:
    - restricted columns must not be 'none' or 'synthetic' alone.
    - confidential columns must not be 'none'.
    - PHI/PII placement (caller responsibility) — we only validate the declared method.
    """
    out: list[TokenizationReview] = []
    for p in policies:
        if p.classification == "restricted" and p.method in ("none", "synthetic"):
            out.append(
                TokenizationReview(
                    p,
                    False,
                    f"restricted column '{p.column}' must use vault/mask/hash, got '{p.method}'",
                )
            )
        elif p.classification == "confidential" and p.method == "none":
            out.append(
                TokenizationReview(
                    p,
                    False,
                    f"confidential column '{p.column}' must declare a protection method",
                )
            )
        else:
            out.append(TokenizationReview(p, True, "policy passes static review"))
    return out
