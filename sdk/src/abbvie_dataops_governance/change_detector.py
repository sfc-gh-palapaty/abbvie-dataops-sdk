"""Implements the AbbVie 'data change gate' for PR governance.

Given a list of changed file paths (typically from `git diff --name-only base..head`
or the GitHub `pull_request` event), decide:

1. Does this PR touch governed data surfaces? (paths under migrations/, schemas/,
   pipelines/, manifests/, apps/*/migrations, etc.)
2. Which manifests should be exercised in `develop` profile on this PR?
3. Should the PR fail closed because a data-change PR lacks required artifacts
   (e.g., schema migration without an updated schemas/ JSON)?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

GOVERNED_PREFIXES: tuple[str, ...] = (
    "migrations/",
    "manifests/",
    "pipelines/",
    "data/ontology/",
    "apps/suitecrm/migrations/",
    "apps/suitecrm/extractor/",
)

MANIFEST_TRIGGERS: dict[str, tuple[str, ...]] = {
    "manifests/snowflake-curated.yaml": ("migrations/snowflake/", "manifests/schemas/snowflake/", "manifests/constraints/snowflake/"),
    "manifests/emr-iceberg-bronze.yaml": ("pipelines/emr/", "manifests/schemas/emr/"),
    "manifests/suitecrm-crm.yaml": ("apps/suitecrm/", "manifests/schemas/suitecrm/", "manifests/constraints/suitecrm/"),
    "manifests/pharma-ontology.yaml": ("data/ontology/", "outputs/ontology/"),
}

REQUIRED_PAIRS: tuple[tuple[str, str], ...] = (
    ("migrations/snowflake/", "manifests/schemas/snowflake/"),
    ("apps/suitecrm/migrations/", "manifests/schemas/suitecrm/"),
    ("pipelines/emr/", "manifests/schemas/emr/"),
)


@dataclass
class ChangeDecision:
    is_data_change: bool
    triggered_manifests: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def must_fail_closed(self) -> bool:
        return self.is_data_change and bool(self.blockers)


def _starts_with_any(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(p) for p in prefixes)


def detect(changed_files: list[str]) -> ChangeDecision:
    paths = [str(PurePosixPath(p)) for p in changed_files]
    is_data_change = any(_starts_with_any(p, GOVERNED_PREFIXES) for p in paths)

    triggered: list[str] = []
    for manifest, prefixes in MANIFEST_TRIGGERS.items():
        if any(_starts_with_any(p, prefixes) for p in paths):
            triggered.append(manifest)

    blockers: list[str] = []
    for change_prefix, contract_prefix in REQUIRED_PAIRS:
        touched_change = any(p.startswith(change_prefix) for p in paths)
        touched_contract = any(p.startswith(contract_prefix) for p in paths)
        if touched_change and not touched_contract:
            blockers.append(
                f"changes under '{change_prefix}' require an updated contract under '{contract_prefix}'"
            )

    return ChangeDecision(
        is_data_change=is_data_change,
        triggered_manifests=triggered,
        blockers=blockers,
    )
