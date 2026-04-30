"""AbbVie DataOps Governance SDK.

Manifest-driven library that any CI/CD pipeline can invoke when a change touches
governed data. Cross-platform via pluggable adapters (Snowflake, EMR, SuiteCRM)
and pluggable emitters (OpenLineage / Marquez, DataHub).
"""

from abbvie_dataops_governance.constraints import ConstraintFinding, ConstraintValidator, ExpectedConstraint
from abbvie_dataops_governance.dq import DataQualityRunner, DQCheck, DQResult, DQSuite
from abbvie_dataops_governance.manifest import Manifest, load_manifest
from abbvie_dataops_governance.schema_enforcement import ExpectedColumn, SchemaDrift, SchemaEnforcer
from abbvie_dataops_governance.tokenization import TokenizationPolicy, TokenizationReview, review_policies

__version__ = "0.2.0"

__all__ = [
    "ConstraintFinding",
    "ConstraintValidator",
    "DataQualityRunner",
    "DQCheck",
    "DQResult",
    "DQSuite",
    "ExpectedColumn",
    "ExpectedConstraint",
    "Manifest",
    "SchemaDrift",
    "SchemaEnforcer",
    "TokenizationPolicy",
    "TokenizationReview",
    "load_manifest",
    "review_policies",
]
