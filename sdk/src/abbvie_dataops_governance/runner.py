"""End-to-end runner: load manifest -> introspect via adapter -> run checks -> emit lineage/catalog."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from abbvie_dataops_governance.adapters import get_adapter
from abbvie_dataops_governance.constraints import ConstraintValidator
from abbvie_dataops_governance.constraints import load_expected as load_constraints
from abbvie_dataops_governance.dq import DataQualityRunner, DQSuite
from abbvie_dataops_governance.emitters.datahub import DataHubEmitter
from abbvie_dataops_governance.emitters.openlineage import OpenLineageEmitter
from abbvie_dataops_governance.manifest import Manifest, load_manifest
from abbvie_dataops_governance.schema_enforcement import SchemaEnforcer
from abbvie_dataops_governance.schema_enforcement import load_expected as load_schema
from abbvie_dataops_governance.tokenization import load_policies, review_policies


@dataclass
class CheckOutcome:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    service: str
    adapter: str
    profile: str
    classification: str
    passed: bool
    outcomes: list[CheckOutcome] = field(default_factory=list)
    adapter_facts: dict[str, Any] = field(default_factory=dict)
    emissions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "adapter": self.adapter,
            "profile": self.profile,
            "classification": self.classification,
            "passed": self.passed,
            "outcomes": [asdict(o) for o in self.outcomes],
            "adapter_facts": self.adapter_facts,
            "emissions": self.emissions,
        }


def run_manifest(manifest_path: str | Path, profile: str | None = None, *, repo_root: Path | None = None) -> EvidenceBundle:
    repo_root = repo_root or Path.cwd()
    manifest: Manifest = load_manifest(manifest_path)
    if profile:
        manifest.profile = profile  # type: ignore[assignment]

    adapter_cls = get_adapter(manifest.adapter)
    adapter = adapter_cls(manifest)
    snap = adapter.introspect()

    bundle = EvidenceBundle(
        service=manifest.service,
        adapter=manifest.adapter,
        profile=manifest.profile,
        classification=manifest.classification,
        passed=True,
        adapter_facts=snap.facts,
    )

    if manifest.checks.schema_enforcement:
        spec = manifest.checks.schema_enforcement
        expected = load_schema(repo_root / spec.expected)
        actual = snap.actual_columns if spec.actual_source == "adapter" else {}
        drift = SchemaEnforcer(actual).diff(expected)
        ok = not drift.is_drift if actual else True
        detail = "no drift" if ok and actual else ("dry-run (no actual cols)" if not actual else "drift detected")
        bundle.outcomes.append(
            CheckOutcome(name="schema_enforcement", passed=ok, detail=detail, data=drift.as_dict())
        )
        bundle.passed = bundle.passed and ok

    if manifest.checks.data_quality and manifest.checks.data_quality.suite:
        suite = DQSuite.from_file(repo_root / manifest.checks.data_quality.suite)
        rows = snap.sample_rows
        runner = DataQualityRunner(row_getter=(lambda: rows) if rows is not None else None)
        results = runner.run(suite)
        all_ok = all(r.passed for r in results)
        bundle.outcomes.append(
            CheckOutcome(
                name="data_quality",
                passed=all_ok or not manifest.checks.data_quality.fail_on_error,
                detail=f"{sum(r.passed for r in results)}/{len(results)} passed",
                data={"results": [{"check": r.check, "kind": r.kind, "passed": r.passed, "detail": r.detail} for r in results]},
            )
        )
        bundle.passed = bundle.passed and (all_ok or not manifest.checks.data_quality.fail_on_error)

    if manifest.checks.constraints:
        expected = load_constraints(repo_root / manifest.checks.constraints.expected)
        validator = ConstraintValidator(snap.constraint_rows)
        findings = validator.validate(expected)
        all_ok = all(f.ok for f in findings)
        bundle.outcomes.append(
            CheckOutcome(
                name="constraints",
                passed=all_ok or not manifest.checks.constraints.fail_on_missing,
                detail=f"{sum(f.ok for f in findings)}/{len(findings)} matched",
                data={"findings": [asdict(f) for f in findings]},
            )
        )
        bundle.passed = bundle.passed and (all_ok or not manifest.checks.constraints.fail_on_missing)

    if manifest.checks.tokenization:
        policies = load_policies(repo_root / manifest.checks.tokenization.classification_map)
        reviews = review_policies(policies)
        all_ok = all(r.compliant for r in reviews)
        bundle.outcomes.append(
            CheckOutcome(
                name="tokenization",
                passed=all_ok,
                detail=f"{sum(r.compliant for r in reviews)}/{len(reviews)} compliant",
                data={"reviews": [{"column": r.policy.column, "classification": r.policy.classification, "method": r.policy.method, "compliant": r.compliant, "detail": r.detail} for r in reviews]},
            )
        )
        bundle.passed = bundle.passed and all_ok

    bundle.emissions = _emit(manifest, snap.actual_columns, bundle.passed)
    return bundle


def _emit(manifest: Manifest, actual_columns: dict[str, str], passed: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ol = OpenLineageEmitter()
    if ol.enabled and manifest.emit.openlineage:
        run_id = OpenLineageEmitter.new_run_id()
        start = ol.emit_run(manifest, "START", run_id, actual_columns=actual_columns)
        end = ol.emit_run(
            manifest,
            "COMPLETE" if passed else "FAIL",
            run_id,
            actual_columns=actual_columns,
        )
        out["openlineage"] = {"run_id": run_id, "start": start, "end": end}
    dh = DataHubEmitter()
    if dh.enabled and manifest.emit.datahub:
        out["datahub"] = dh.emit_dataset(manifest, actual_columns=actual_columns)
    return out


def write_evidence(bundle: EvidenceBundle, path: str | Path) -> None:
    Path(path).write_text(json.dumps(bundle.to_dict(), indent=2, default=str), encoding="utf-8")
