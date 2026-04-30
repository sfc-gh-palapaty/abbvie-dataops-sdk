"""Schema enforcement: detect drift between expected contract and deployed columns."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExpectedColumn:
    name: str
    data_type: str
    nullable: bool = True


@dataclass
class SchemaDrift:
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    type_mismatches: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def is_drift(self) -> bool:
        return bool(self.missing or self.extra or self.type_mismatches)

    def as_dict(self) -> dict[str, Any]:
        return {
            "missing": list(self.missing),
            "extra": list(self.extra),
            "type_mismatches": [
                {"column": c, "expected": e, "actual": a} for c, e, a in self.type_mismatches
            ],
        }


def load_expected(path: str | Path) -> list[ExpectedColumn]:
    """Read a JSON contract: either a flat {col:type} map or a list of {name,data_type,nullable}."""
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "columns" in payload:
        payload = payload["columns"]
    if isinstance(payload, dict):
        return [ExpectedColumn(name=k, data_type=str(v)) for k, v in payload.items()]
    if isinstance(payload, list):
        out: list[ExpectedColumn] = []
        for item in payload:
            out.append(
                ExpectedColumn(
                    name=item["name"],
                    data_type=item["data_type"],
                    nullable=bool(item.get("nullable", True)),
                )
            )
        return out
    raise ValueError(f"unsupported schema contract shape in {p}")


class SchemaEnforcer:
    def __init__(self, actual_columns: dict[str, str] | None = None):
        """`actual_columns` maps column_name -> data_type as reported by the adapter."""
        self._actual = actual_columns or {}

    def diff(self, expected: list[ExpectedColumn]) -> SchemaDrift:
        exp_map = {c.name.lower(): c for c in expected}
        act_map = {k.lower(): v for k, v in self._actual.items()}
        missing = [c.name for c in expected if c.name.lower() not in act_map]
        extra = [k for k in act_map if k not in exp_map]
        mismatches: list[tuple[str, str, str]] = []
        for name, col in exp_map.items():
            if name in act_map:
                actual_type = act_map[name].lower()
                expected_type = col.data_type.lower()
                if actual_type != expected_type:
                    mismatches.append((col.name, expected_type, actual_type))
        return SchemaDrift(missing=missing, extra=extra, type_mismatches=mismatches)

    def enforce(self, expected: list[ExpectedColumn]) -> SchemaDrift:
        drift = self.diff(expected)
        if drift.is_drift:
            parts = []
            if drift.missing:
                parts.append(f"missing: {drift.missing}")
            if drift.extra:
                parts.append(f"extra: {drift.extra}")
            if drift.type_mismatches:
                parts.append(f"type_mismatches: {drift.type_mismatches}")
            raise ValueError("schema drift detected — " + "; ".join(parts))
        return drift
