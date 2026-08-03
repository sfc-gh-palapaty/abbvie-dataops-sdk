"""Build Open Semantic Interchange (OSI / Apache Ossie) YAML from parsed ontology."""

from __future__ import annotations

import json
from typing import Any

import yaml

from abbvie_dataops_governance.ontology.parsers import Entity, MappingRow, ParsedOntology, Relationship

OSI_VERSION = "0.1.1"

_DTYPE_MAP = {
    "STRING": "String",
    "INTEGER": "Integer",
    "BOOLEAN": "Boolean",
    "DATE": "Date",
    "FLOAT": "Decimal",
    "DECIMAL": "Decimal",
}

_ENTITY_TO_DATASET = {
    "patient": "patients",
    "drug": "drugs",
    "prescriber": "prescribers",
    "facility": "facilities",
    "prescription": "prescriptions",
    "therapy_area": "therapy_areas",
    "treatment_pathway": "treatment_pathways",
    "adverse_event": "adverse_events",
}


def _field_block(name: str, dtype: str, description: str = "", *, is_time: bool = False) -> dict[str, Any]:
    block: dict[str, Any] = {
        "name": name,
        "expression": {
            "dialects": [
                {"dialect": "ANSI_SQL", "expression": name},
                {"dialect": "SNOWFLAKE", "expression": name},
            ]
        },
        "datatype": _DTYPE_MAP.get(dtype.upper(), "String"),
        "dimension": {"is_time": is_time},
    }
    if description:
        block["description"] = description
    return block


def _target_table_for_entity(entity: Entity, mappings: list[MappingRow], database: str, schema: str) -> str:
    entity_mappings = [m for m in mappings if m.entity == entity.name]
    if entity_mappings:
        table = entity_mappings[0].target_table.lower()
        return f"{database}.{schema}.{table}"
    dataset = _ENTITY_TO_DATASET.get(entity.name, entity.name)
    return f"{database}.{schema}.{dataset}"


def _primary_key(entity: Entity) -> list[str]:
    pks = [f.name for f in entity.fields if f.is_pk]
    if pks:
        return pks
    if entity.fields:
        return [entity.fields[0].name]
    return []


def _build_dataset(entity: Entity, mappings: list[MappingRow], database: str, schema: str) -> dict[str, Any]:
    entity_mappings = {m.target_column: m for m in mappings if m.entity == entity.name}
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()

    for field in entity.fields:
        mapping = entity_mappings.get(field.name)
        desc_parts = []
        if mapping and mapping.business_rule:
            desc_parts.append(mapping.business_rule)
        if mapping and mapping.transformation:
            desc_parts.append(f"Transform: {mapping.transformation}")
        if field.enum_values:
            desc_parts.append(f"Allowed: {', '.join(field.enum_values)}")
        fields.append(
            _field_block(
                field.name,
                field.data_type,
                "; ".join(desc_parts),
                is_time=field.data_type.upper() == "DATE" and "date" in field.name,
            )
        )
        seen.add(field.name)

    for mapping in entity_mappings.values():
        if mapping.target_column not in seen:
            fields.append(
                _field_block(
                    mapping.target_column,
                    mapping.data_type,
                    mapping.business_rule or mapping.notes,
                    is_time=mapping.data_type.upper() == "DATE",
                )
            )

    return {
        "name": _ENTITY_TO_DATASET.get(entity.name, entity.name),
        "source": _target_table_for_entity(entity, mappings, database, schema),
        "primary_key": _primary_key(entity),
        "description": f"AbbVie pharma entity: {entity.name}",
        "fields": fields,
    }


def _build_relationships(
    relationships: list[Relationship],
    entity_names: set[str],
    pk_map: dict[str, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in relationships:
        if rel.from_entity not in entity_names or rel.to_entity not in entity_names:
            continue
        if rel.from_entity == rel.to_entity:
            continue
        from_ds = _ENTITY_TO_DATASET.get(rel.from_entity, rel.from_entity)
        to_ds = _ENTITY_TO_DATASET.get(rel.to_entity, rel.to_entity)
        from_col = pk_map.get(rel.from_entity, f"{rel.from_entity}_id")
        to_col = pk_map.get(rel.to_entity, f"{rel.to_entity}_id")
        out.append(
            {
                "name": rel.name,
                "from": from_ds,
                "to": to_ds,
                "from_columns": [from_col],
                "to_columns": [to_col],
                "description": rel.description or rel.cardinality,
            }
        )
    return out


def _build_metrics(parsed: ParsedOntology) -> list[dict[str, Any]]:
    return [
        {
            "name": "total_prescriptions",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "COUNT(prescriptions.rx_id)"},
                    {"dialect": "SNOWFLAKE", "expression": "COUNT(prescriptions.rx_id)"},
                ]
            },
            "description": "Total prescription count across the governed pharma model",
            "datatype": "Integer",
        },
        {
            "name": "switch_prescriptions",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "COUNT(prescriptions.switch_from_drug_id)"},
                    {"dialect": "SNOWFLAKE", "expression": "COUNT(prescriptions.switch_from_drug_id)"},
                ]
            },
            "description": "Prescriptions with a treatment switch (switch_from_drug_id populated)",
            "datatype": "Integer",
        },
        {
            "name": "kol_prescriber_count",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "COUNT(prescribers.prescriber_id)"},
                    {"dialect": "SNOWFLAKE", "expression": "COUNT(prescribers.prescriber_id)"},
                ]
            },
            "description": "Prescriber count (filter is_kol in queries)",
            "datatype": "Integer",
        },
        {
            "name": "patients_on_therapy",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "COUNT(patients.patient_id)"},
                    {"dialect": "SNOWFLAKE", "expression": "COUNT(patients.patient_id)"},
                ]
            },
            "description": "Distinct patients in the active cohort",
            "datatype": "Integer",
        },
    ]


def build_osi_model(
    parsed: ParsedOntology,
    *,
    model_name: str = "abbvie_pharma_intelligence",
    ontology_version: str = "2.1.0",
    database: str = "ABBVIE_DATAOPS_DEV",
    schema: str = "CURATED",
) -> dict[str, Any]:
    datasets = [_build_dataset(e, parsed.mappings, database, schema) for e in parsed.entities]
    entity_names = {e.name for e in parsed.entities}
    pk_map = {e.name: _primary_key(e)[0] for e in parsed.entities if _primary_key(e)}
    relationships = _build_relationships(parsed.relationships, entity_names, pk_map)
    metrics = _build_metrics(parsed)

    extension_payload = {
        "ontology_version": ontology_version,
        "abstract_classes": parsed.abstract_classes,
        "inference_rules": parsed.inference_rules,
        "hierarchy": parsed.hierarchy,
        "business_rules": [
            {"category": r.category, "name": r.name, "description": r.description[:300]}
            for r in parsed.business_rules
        ],
        "source_documents": ["pharma_erd.md", "business_rules.md", "source_to_target.csv"],
        "materialization_targets": ["snowflake_semantic_view", "aws_glue_data_catalog"],
    }

    return {
        "version": OSI_VERSION,
        "semantic_model": [
            {
                "name": model_name,
                "description": "AbbVie Pharma Intelligence Platform — governed semantic model derived from business documents",
                "ai_context": (
                    "Use for AbbVie pharma analytics: patient cohorts, prescription trends, "
                    "treatment switching, KOL identification, and adverse event analysis. "
                    "Prefer certified datasets and respect therapy area hierarchy. "
                    "Example queries: treatment switch rate by therapy area; KOL prescriber concentration by facility."
                ),
                "datasets": datasets,
                "relationships": relationships,
                "metrics": metrics,
                "custom_extensions": [
                    {
                        "vendor_name": "ABBVIE",
                        "data": json.dumps(extension_payload),
                    },
                    {
                        "vendor_name": "SNOWFLAKE",
                        "data": json.dumps(
                            {
                                "import_procedure": "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML",
                                "target_schema": f"{database}.{schema}",
                            }
                        ),
                    },
                ],
            }
        ],
    }


def render_osi_yaml(model: dict[str, Any]) -> str:
    return yaml.dump(model, sort_keys=False, default_flow_style=False, allow_unicode=True)
