"""End-to-end ontology build: read docs → parse → emit OSI YAML → write versioned outputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from abbvie_dataops_governance.ontology.document_reader import DocumentBundle, read_documents, read_s3_prefix
from abbvie_dataops_governance.ontology.osi_builder import build_osi_model, render_osi_yaml
from abbvie_dataops_governance.ontology.parsers import parse_all


@dataclass
class OntologyBuildResult:
    model_name: str
    ontology_version: str
    output_path: Path
    manifest_path: Path
    yaml_content: str
    content_hash: str
    datasets: int
    relationships: int
    metrics: int
    sources: dict[str, str] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "ontology_version": self.ontology_version,
            "output_path": str(self.output_path),
            "manifest_path": str(self.manifest_path),
            "content_hash": self.content_hash,
            "datasets": self.datasets,
            "relationships": self.relationships,
            "metrics": self.metrics,
            "sources": self.sources,
            "facts": self.facts,
        }


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def build_ontology(
    *,
    erd_source: str,
    business_rules_source: str,
    source_to_target_source: str,
    output_dir: str | Path,
    model_name: str = "abbvie_pharma_intelligence",
    ontology_version: str = "2.1.0",
    target_database: str = "ABBVIE_DATAOPS_DEV",
    target_schema: str = "CURATED",
    repo_root: Path | None = None,
    s3_bucket: str | None = None,
    s3_prefix: str | None = None,
) -> OntologyBuildResult:
    root = repo_root or Path.cwd()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)

    if s3_bucket and s3_prefix:
        bundle: DocumentBundle = read_s3_prefix(s3_bucket, s3_prefix)
    else:
        bundle = read_documents(
            erd_source=erd_source,
            business_rules_source=business_rules_source,
            source_to_target_source=source_to_target_source,
            repo_root=root,
        )

    parsed = parse_all(bundle.erd, bundle.business_rules, bundle.source_to_target)
    model = build_osi_model(
        parsed,
        model_name=model_name,
        ontology_version=ontology_version,
        database=target_database,
        schema=target_schema,
    )
    yaml_content = render_osi_yaml(model)
    content_hash = _content_hash(yaml_content)

    output_file = out / f"{model_name}_v{ontology_version}.yaml"
    output_file.write_text(yaml_content, encoding="utf-8")

    manifest = {
        "model_name": model_name,
        "ontology_version": ontology_version,
        "osi_version": model["version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "content_hash": content_hash,
        "output_file": output_file.name,
        "sources": bundle.sources,
        "stats": {
            "entities": len(parsed.entities),
            "relationships": len(parsed.relationships),
            "mappings": len(parsed.mappings),
            "business_rules": len(parsed.business_rules),
            "metrics": len(model["semantic_model"][0]["metrics"]),
        },
        "materialization": {
            "snowflake": {
                "procedure": "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML",
                "schema": f"{target_database}.{target_schema}",
            },
            "aws": {
                "note": "Import OSI YAML via Glue Data Catalog semantic layer or custom converter",
            },
        },
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    sm = model["semantic_model"][0]
    return OntologyBuildResult(
        model_name=model_name,
        ontology_version=ontology_version,
        output_path=output_file,
        manifest_path=manifest_path,
        yaml_content=yaml_content,
        content_hash=content_hash,
        datasets=len(sm["datasets"]),
        relationships=len(sm["relationships"]),
        metrics=len(sm["metrics"]),
        sources=bundle.sources,
        facts={
            "entities": [e.name for e in parsed.entities],
            "abstract_classes": parsed.abstract_classes,
            "hierarchy_roots": list(parsed.hierarchy.keys()),
        },
    )
