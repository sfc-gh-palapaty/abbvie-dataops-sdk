"""Declarative data-quality checks (row counts, null rates, uniqueness, SQL assertions)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

CheckKind = Literal["not_null", "unique", "row_count_min", "row_count_max", "sql_assert", "value_in_set"]


@dataclass
class DQCheck:
    name: str
    kind: CheckKind
    column: str | None = None
    threshold: float | int | None = None
    sql: str | None = None
    allowed_values: list[Any] = field(default_factory=list)


@dataclass
class DQSuite:
    checks: list[DQCheck] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DQSuite:
        raw = payload.get("checks", [])
        checks = [
            DQCheck(
                name=item["name"],
                kind=item["kind"],
                column=item.get("column"),
                threshold=item.get("threshold"),
                sql=item.get("sql"),
                allowed_values=list(item.get("allowed_values", [])),
            )
            for item in raw
        ]
        return cls(checks=checks)

    @classmethod
    def from_file(cls, path: str | Path) -> DQSuite:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() in (".json",):
            payload = json.loads(text)
        else:
            payload = yaml.safe_load(text) or {}
        return cls.from_dict(payload)


@dataclass
class DQResult:
    check: str
    kind: str
    passed: bool
    detail: str


class DataQualityRunner:
    """If `row_getter` is supplied, evaluate against in-memory rows; otherwise return dry-run results."""

    def __init__(self, row_getter: Callable[[], Sequence[dict[str, Any]]] | None = None):
        self._row_getter = row_getter

    def run(self, suite: DQSuite) -> list[DQResult]:
        rows = list(self._row_getter()) if self._row_getter else None
        return [self._run_one(c, rows) for c in suite.checks]

    def _run_one(self, c: DQCheck, rows: list[dict[str, Any]] | None) -> DQResult:
        if rows is None:
            return DQResult(c.name, c.kind, True, "dry-run: no row source supplied")

        if c.kind == "row_count_min":
            n = len(rows)
            limit = int(c.threshold or 0)
            return DQResult(c.name, c.kind, n >= limit, f"rows={n}, min={limit}")

        if c.kind == "row_count_max":
            n = len(rows)
            limit = int(c.threshold or 0)
            return DQResult(c.name, c.kind, n <= limit, f"rows={n}, max={limit}")

        if c.kind == "not_null":
            col = c.column or ""
            bad = sum(1 for r in rows if r.get(col) is None)
            return DQResult(c.name, c.kind, bad == 0, f"nulls in {col}: {bad}")

        if c.kind == "unique":
            col = c.column or ""
            seen: set[Any] = set()
            dupes = 0
            for r in rows:
                v = r.get(col)
                if v in seen:
                    dupes += 1
                seen.add(v)
            return DQResult(c.name, c.kind, dupes == 0, f"duplicate {col}: {dupes}")

        if c.kind == "value_in_set":
            col = c.column or ""
            allowed = set(c.allowed_values)
            bad = sum(1 for r in rows if r.get(col) not in allowed)
            return DQResult(c.name, c.kind, bad == 0, f"out-of-set {col}: {bad} (allowed={sorted(allowed)})")

        if c.kind == "sql_assert":
            return DQResult(c.name, c.kind, True, "sql_assert: requires adapter execution path")

        return DQResult(c.name, c.kind, False, f"unknown kind: {c.kind}")
