"""Model and validate relational constraints (PK / FK / unique / not-null) declared per service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

ConstraintType = Literal["primary_key", "foreign_key", "unique", "not_null"]


@dataclass(frozen=True)
class ExpectedConstraint:
    name: str
    constraint_type: ConstraintType
    table: str
    columns: tuple[str, ...]
    references_table: str | None = None
    references_columns: tuple[str, ...] | None = None


@dataclass
class ConstraintFinding:
    constraint: str
    ok: bool
    message: str


def load_expected(path: str | Path) -> list[ExpectedConstraint]:
    p = Path(path)
    payload = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    items = payload.get("expected", payload if isinstance(payload, list) else [])
    out: list[ExpectedConstraint] = []
    for c in items:
        out.append(
            ExpectedConstraint(
                name=c["name"],
                constraint_type=c["type"],
                table=c["table"],
                columns=tuple(c["columns"]),
                references_table=c.get("references_table"),
                references_columns=tuple(c["references_columns"]) if c.get("references_columns") else None,
            )
        )
    return out


class ConstraintValidator:
    """Compare declared constraints to an INFORMATION_SCHEMA snapshot supplied by the adapter."""

    def __init__(self, information_schema_rows: list[dict[str, Any]] | None = None):
        self._rows = information_schema_rows

    def validate(self, expected: list[ExpectedConstraint]) -> list[ConstraintFinding]:
        if self._rows is None:
            return [ConstraintFinding(e.name, True, "dry-run: no INFORMATION_SCHEMA snapshot") for e in expected]
        return [self._match(e) for e in expected]

    def _match(self, exp: ExpectedConstraint) -> ConstraintFinding:
        key = (exp.table.lower(), exp.name.lower())
        for row in self._rows:
            if (row.get("table_name", "").lower(), row.get("constraint_name", "").lower()) == key:
                return ConstraintFinding(exp.name, True, "found in INFORMATION_SCHEMA")
        return ConstraintFinding(exp.name, False, "missing in INFORMATION_SCHEMA snapshot")
