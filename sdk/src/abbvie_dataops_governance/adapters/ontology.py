"""Ontology adapter: reads business documents and builds OSI semantic models."""

from __future__ import annotations

from typing import Any

from abbvie_dataops_governance.adapters.base import Adapter, AdapterResult
from abbvie_dataops_governance.ontology.pipeline import build_ontology


class OntologyAdapter(Adapter):
    name = "ontology"

    def introspect(self) -> AdapterResult:
        conn = self.manifest.connection
        spec = self.manifest.checks.ontology
        if not spec:
            return AdapterResult(facts={"note": "ontology adapter missing checks.ontology block — dry-run"})

        try:
            result = build_ontology(
                erd_source=spec.erd_source,
                business_rules_source=spec.business_rules_source,
                source_to_target_source=spec.source_to_target_source,
                output_dir=spec.output_dir,
                model_name=spec.model_name,
                ontology_version=spec.ontology_version,
                target_database=spec.target_database,
                target_schema=spec.target_schema,
                repo_root=self.repo_root,
                s3_bucket=conn.s3_bucket,
                s3_prefix=conn.s3_prefix,
            )
        except FileNotFoundError as exc:
            return AdapterResult(facts={"note": f"ontology source not found — dry-run: {exc}"})
        except Exception as exc:
            return AdapterResult(facts={"note": f"ontology build failed — dry-run: {exc}"})

        columns = {d: "osi_field" for d in [f"dataset_{i}" for i in range(result.datasets)]}
        facts: dict[str, Any] = {
            "model_name": result.model_name,
            "ontology_version": result.ontology_version,
            "output_path": str(result.output_path),
            "content_hash": result.content_hash,
            "datasets": result.datasets,
            "relationships": result.relationships,
            "metrics": result.metrics,
            "sources": result.sources,
            **result.facts,
        }
        return AdapterResult(actual_columns=columns, facts=facts)
