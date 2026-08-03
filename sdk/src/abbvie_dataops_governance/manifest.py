"""Pydantic schema for `dataops-manifest.yaml` consumed by the SDK CLI.

A manifest declares (1) the service, (2) which platform adapter to use,
(3) which checks to run, and (4) where to emit lineage / catalog events.
The SDK is **driven entirely** by the manifest -- no per-pipeline code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

AdapterName = Literal["snowflake", "emr", "suitecrm", "ontology"]
ProfileName = Literal["develop", "build", "promote"]
Classification = Literal["public", "internal", "confidential", "restricted"]


class SchemaEnforcementSpec(BaseModel):
    expected: str = Field(..., description="Path to expected schema JSON (column -> type)")
    actual_source: Literal["adapter", "manifest", "skip"] = "adapter"


class DataQualitySpec(BaseModel):
    suite: str | None = Field(None, description="Path to a DQ suite YAML/JSON")
    fail_on_error: bool = True


class ConstraintSpec(BaseModel):
    expected: str = Field(..., description="Path to expected constraints YAML")
    fail_on_missing: bool = True


class TokenizationSpec(BaseModel):
    classification_map: str = Field(..., description="Path to classification + method YAML")


class OntologySpec(BaseModel):
    model_config = {"protected_namespaces": ()}

    erd_source: str = "data/ontology/pharma_erd.md"
    business_rules_source: str = "data/ontology/business_rules.md"
    source_to_target_source: str = "data/ontology/source_to_target.csv"
    output_dir: str = "outputs/ontology"
    model_name: str = "abbvie_pharma_intelligence"
    ontology_version: str = "2.1.0"
    target_database: str = "ABBVIE_DATAOPS_DEV"
    target_schema: str = "CURATED"
    min_datasets: int = 5
    min_relationships: int = 3
    min_metrics: int = 2


class ChecksBlock(BaseModel):
    schema_enforcement: SchemaEnforcementSpec | None = None
    data_quality: DataQualitySpec | None = None
    constraints: ConstraintSpec | None = None
    tokenization: TokenizationSpec | None = None
    ontology: OntologySpec | None = None


class OpenLineageEmit(BaseModel):
    namespace: str
    job: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class DataHubEmit(BaseModel):
    platform: str
    env: str = "PROD"
    dataset_urn_template: str = (
        "urn:li:dataset:(urn:li:dataPlatform:{platform},{db}.{schema}.{table},{env})"
    )
    datasets: list[dict] = Field(default_factory=list)
    upstream_urns: list[str] = Field(default_factory=list)


class EmitBlock(BaseModel):
    openlineage: OpenLineageEmit | None = None
    datahub: DataHubEmit | None = None


class AdapterConnection(BaseModel):
    """Free-form connection hints; adapters interpret keys they need."""

    snowflake_account_secret: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None
    snowflake_table: str | None = None

    glue_database: str | None = None
    glue_table: str | None = None
    s3_uri: str | None = None

    suitecrm_db_secret_arn: str | None = None
    suitecrm_table: str | None = None

    s3_bucket: str | None = None
    s3_prefix: str | None = None


class Manifest(BaseModel):
    service: str
    owners: list[str] = Field(default_factory=list)
    classification: Classification = "internal"
    adapter: AdapterName
    profile: ProfileName = "develop"
    connection: AdapterConnection = Field(default_factory=AdapterConnection)
    checks: ChecksBlock = Field(default_factory=ChecksBlock)
    emit: EmitBlock = Field(default_factory=EmitBlock)

    @field_validator("owners")
    @classmethod
    def _owners_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("manifest.owners must list at least one owner")
        return v


def load_manifest(path: str | Path) -> Manifest:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Manifest.model_validate(raw)
