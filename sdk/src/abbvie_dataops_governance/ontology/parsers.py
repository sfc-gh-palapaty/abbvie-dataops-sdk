"""Parse AbbVie pharma business documents into structured ontology models."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field


@dataclass
class EntityField:
    name: str
    data_type: str
    is_pk: bool = False
    is_fk: bool = False
    fk_target: str | None = None
    enum_values: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Entity:
    name: str
    fields: list[EntityField] = field(default_factory=list)


@dataclass
class Relationship:
    name: str
    from_entity: str
    to_entity: str
    cardinality: str = ""
    description: str = ""


@dataclass
class MappingRow:
    entity: str
    attribute: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    transformation: str
    business_rule: str
    data_type: str
    nullable: bool
    notes: str


@dataclass
class BusinessRule:
    category: str
    name: str
    description: str


@dataclass
class ParsedOntology:
    entities: list[Entity]
    relationships: list[Relationship]
    mappings: list[MappingRow]
    business_rules: list[BusinessRule]
    abstract_classes: dict[str, list[str]]
    inference_rules: list[str]
    hierarchy: dict[str, list[str]]
    version: str = "2.1"


_FIELD_RE = re.compile(
    r"^-\s+(\w+)\s+(?:\((PK|FK(?:\s*→\s*(\w+))?)\)\s+)?:\s+(\w+(?:\s*\{[^}]+\})?)",
    re.MULTILINE,
)
_ENTITY_RE = re.compile(r"^###\s+(\w+)", re.MULTILINE)
_REL_RE = re.compile(
    r"^(\w+)\s+--\[(.+?)\]-->\s+(\w+)\s*(?:\(([^)]+)\))?",
    re.MULTILINE,
)
_HIER_CHILD_RE = re.compile(r"^│\s*├──\s+(.+)$", re.MULTILINE)
_HIER_ROOT_RE = re.compile(r"^├──\s+(\w+)", re.MULTILINE)


def parse_erd(text: str) -> tuple[list[Entity], list[Relationship], dict[str, list[str]], list[str]]:
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    hierarchy: dict[str, list[str]] = {}
    inference_rules: list[str] = []

    entity_names = _ENTITY_RE.findall(text)
    sections = re.split(r"^###\s+", text, flags=re.MULTILINE)[1:]

    for section in sections:
        lines = section.splitlines()
        if not lines:
            continue
        entity_name = lines[0].strip()
        entity_name = re.sub(r"\s*\([^)]*\)", "", entity_name).strip().lower()
        body = "\n".join(lines[1:])
        fields: list[EntityField] = []
        for match in _FIELD_RE.finditer(body):
            fname, role, fk_target, raw_type = match.groups()
            enum_values: list[str] = []
            dtype = raw_type
            enum_match = re.search(r"\{([^}]+)\}", raw_type)
            if enum_match:
                enum_values = [v.strip() for v in enum_match.group(1).split(",")]
                dtype = raw_type.split("{")[0].strip()
            fields.append(
                EntityField(
                    name=fname.lower(),
                    data_type=dtype,
                    is_pk=role == "PK",
                    is_fk=bool(role and role.startswith("FK")),
                    fk_target=fk_target.lower() if fk_target else None,
                    enum_values=enum_values,
                )
            )
        entities.append(Entity(name=entity_name.lower(), fields=fields))

    rel_section = re.search(r"## RELATIONSHIPS\s*\n(.+?)(?:\n## |\Z)", text, re.DOTALL)
    if rel_section:
        for match in _REL_RE.finditer(rel_section.group(1)):
            from_e, rel_name, to_e, cardinality = match.groups()
            relationships.append(
                Relationship(
                    name=rel_name.strip().lower(),
                    from_entity=from_e.lower(),
                    to_entity=to_e.lower(),
                    cardinality=cardinality or "",
                )
            )

    hier_section = re.search(r"## HIERARCHY\s*\n(.+?)(?:\n## |\Z)", text, re.DOTALL)
    if hier_section:
        current_root = ""
        for line in hier_section.group(1).splitlines():
            root_match = _HIER_ROOT_RE.match(line)
            if root_match:
                current_root = root_match.group(1).strip().lower()
                hierarchy.setdefault(current_root, [])
                continue
            child_match = _HIER_CHILD_RE.match(line)
            if child_match and current_root:
                hierarchy.setdefault(current_root, []).append(child_match.group(1).strip().lower())

    infer_section = re.search(r"## INFERENCE RULES\s*\n(.+?)(?:\n## |\Z)", text, re.DOTALL)
    if infer_section:
        for line in infer_section.group(1).splitlines():
            line = line.strip()
            if line and re.match(r"^\d+\.", line):
                inference_rules.append(re.sub(r"^\d+\.\s*", "", line))

    _ = entity_names
    return entities, relationships, hierarchy, inference_rules


def parse_source_to_target(text: str) -> list[MappingRow]:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[MappingRow] = []
    for row in reader:
        rows.append(
            MappingRow(
                entity=row["ENTITY"].strip().lower(),
                attribute=row["ATTRIBUTE"].strip().lower().replace(" ", "_"),
                source_table=row["SOURCE_TABLE"].strip(),
                source_column=row["SOURCE_COLUMN"].strip(),
                target_table=row["TARGET_TABLE"].strip(),
                target_column=row["TARGET_COLUMN"].strip().lower(),
                transformation=row.get("TRANSFORMATION", "").strip(),
                business_rule=row.get("BUSINESS_RULE", "").strip(),
                data_type=row.get("DATA_TYPE", "STRING").strip(),
                nullable=row.get("NULLABLE", "Y").strip().upper() == "Y",
                notes=row.get("NOTES", "").strip(),
            )
        )
    return rows


def parse_business_rules(text: str) -> tuple[list[BusinessRule], dict[str, list[str]], list[str]]:
    rules: list[BusinessRule] = []
    abstract_classes: dict[str, list[str]] = {}
    inference_rules: list[str] = []

    version_match = re.search(r"Version\s+([\d.]+)", text)
    version = version_match.group(1) if version_match else "2.1"

    table_rows = re.findall(
        r"^\|\s*(\w[\w\s]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        text,
        re.MULTILINE,
    )
    for col1, col2, col3 in table_rows:
        c1, c2, c3 = col1.strip(), col2.strip(), col3.strip()
        if c1 in ("Abstract Class", "Relationship", "Known Fact", "Chain", "Individual Facts"):
            continue
        if "Concrete Subclasses" in c1 or "From" in c1 or "Inferred Fact" in c1:
            continue
        if c1 == "PharmaEntity":
            abstract_classes[c1] = [s.strip() for s in c2.split(",") if s.strip()]
        elif c1 in ("TherapeuticProduct", "CareProvider", "CareRecipient", "ClassificationScheme", "ClinicalEvent", "CareGuideline"):
            abstract_classes[c1] = [s.strip() for s in c2.split(",") if s.strip()]
            rules.append(BusinessRule(category="entity_classification", name=c1, description=c3))
        elif c1 in ("IS_PRESCRIBED", "PRESCRIBES", "TREATS", "WORKS_AT", "SPECIALIZES_IN", "EXPERIENCES", "CAUSED_BY", "FOLLOWS_PATHWAY", "PRECEDES", "PARENT_OF"):
            rules.append(BusinessRule(category="relationship", name=c1, description=c3))

    for match in re.finditer(r"### Rule \d+:\s*(.+?)\n(.+?)(?=\n### |\n---|\Z)", text, re.DOTALL):
        title = match.group(1).strip()
        body = " ".join(line.strip() for line in match.group(2).splitlines() if line.strip())
        rules.append(BusinessRule(category="inference", name=title, description=body))
        inference_rules.append(f"{title}: {body[:200]}")

    switch_section = re.search(r"## SLIDE 5:.+?\n(.+?)(?:\n---|\Z)", text, re.DOTALL)
    if switch_section:
        rules.append(
            BusinessRule(
                category="treatment_switching",
                name="switch_detection",
                description=switch_section.group(1).strip()[:500],
            )
        )

    kol_section = re.search(r"## SLIDE 6:.+?\n(.+?)(?:\n---|\Z)", text, re.DOTALL)
    if kol_section:
        rules.append(
            BusinessRule(
                category="kol_identification",
                name="kol_classification",
                description=kol_section.group(1).strip()[:500],
            )
        )

    return rules, abstract_classes, inference_rules


def parse_all(erd: str, business_rules: str, source_to_target: str) -> ParsedOntology:
    entities, relationships, hierarchy, erd_inference = parse_erd(erd)
    mappings = parse_source_to_target(source_to_target)
    rules, abstract_classes, br_inference = parse_business_rules(business_rules)
    return ParsedOntology(
        entities=entities,
        relationships=relationships,
        mappings=mappings,
        business_rules=rules,
        abstract_classes=abstract_classes,
        inference_rules=erd_inference + br_inference,
        hierarchy=hierarchy,
    )
