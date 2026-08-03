"""Tests for the AbbVie pharma ontology → OSI pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml

from abbvie_dataops_governance.ontology.osi_builder import OSI_VERSION, build_osi_model
from abbvie_dataops_governance.ontology.parsers import parse_all
from abbvie_dataops_governance.ontology.pipeline import build_ontology

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data" / "ontology"


def _load_docs() -> tuple[str, str, str]:
    return (
        (DATA / "pharma_erd.md").read_text(encoding="utf-8"),
        (DATA / "business_rules.md").read_text(encoding="utf-8"),
        (DATA / "source_to_target.csv").read_text(encoding="utf-8"),
    )


def test_parse_erd_entities() -> None:
    erd, rules, mapping = _load_docs()
    parsed = parse_all(erd, rules, mapping)
    entity_names = {e.name for e in parsed.entities}
    assert "patient" in entity_names
    assert "drug" in entity_names
    assert "prescription" in entity_names
    assert len(parsed.entities) >= 8
    assert len(parsed.mappings) >= 20


def test_parse_business_rules() -> None:
    erd, rules, mapping = _load_docs()
    parsed = parse_all(erd, rules, mapping)
    assert "TherapeuticProduct" in parsed.abstract_classes
    assert any(r.category == "treatment_switching" for r in parsed.business_rules)


def test_build_osi_model_structure() -> None:
    erd, rules, mapping = _load_docs()
    parsed = parse_all(erd, rules, mapping)
    model = build_osi_model(parsed)
    assert model["version"] == OSI_VERSION
    sm = model["semantic_model"][0]
    assert sm["name"] == "abbvie_pharma_intelligence"
    assert len(sm["datasets"]) >= 8
    assert len(sm["relationships"]) >= 9
    assert len(sm["metrics"]) >= 4
    assert sm["datasets"][0]["primary_key"]
    assert "custom_extensions" in sm


def test_build_ontology_writes_output(tmp_path: Path) -> None:
    result = build_ontology(
        erd_source=str(DATA / "pharma_erd.md"),
        business_rules_source=str(DATA / "business_rules.md"),
        source_to_target_source=str(DATA / "source_to_target.csv"),
        output_dir=tmp_path,
        repo_root=REPO_ROOT,
    )
    assert result.output_path.exists()
    assert result.manifest_path.exists()
    loaded = yaml.safe_load(result.output_path.read_text(encoding="utf-8"))
    assert loaded["version"] == OSI_VERSION
    assert result.datasets >= 8
