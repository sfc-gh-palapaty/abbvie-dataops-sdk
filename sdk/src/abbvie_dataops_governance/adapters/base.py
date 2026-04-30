"""Adapter contract every platform plugin must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from abbvie_dataops_governance.manifest import Manifest


@dataclass
class AdapterResult:
    actual_columns: dict[str, str] = field(default_factory=dict)
    constraint_rows: list[dict[str, Any]] | None = None
    sample_rows: list[dict[str, Any]] | None = None
    facts: dict[str, Any] = field(default_factory=dict)


class Adapter(ABC):
    name: str = "base"

    def __init__(self, manifest: Manifest):
        self.manifest = manifest

    @abstractmethod
    def introspect(self) -> AdapterResult:
        """Return the deployed-state snapshot used by schema/constraint/DQ checks."""

    def lineage_namespace(self) -> str:
        return self.manifest.emit.openlineage.namespace if self.manifest.emit.openlineage else f"abbvie.{self.name}"
