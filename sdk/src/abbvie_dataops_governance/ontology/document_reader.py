"""Read business documents from local paths or S3 (SharePoint stand-in for demo)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

DocKind = Literal["erd", "business_rules", "source_to_target"]


@dataclass
class DocumentBundle:
    erd: str
    business_rules: str
    source_to_target: str
    sources: dict[str, str]


def _read_local(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_s3_uri(uri: str) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 required for S3 document reads; pip install abbvie-dataops-governance-sdk[aws]") from exc

    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    client = boto3.client("s3")
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")


def _resolve_source(source: str, repo_root: Path) -> tuple[str, str]:
    if source.startswith("s3://"):
        return _read_s3_uri(source), source
    path = Path(source)
    if not path.is_absolute():
        path = repo_root / path
    return _read_local(path), str(path)


def read_documents(
    *,
    erd_source: str,
    business_rules_source: str,
    source_to_target_source: str,
    repo_root: Path,
) -> DocumentBundle:
    erd, erd_ref = _resolve_source(erd_source, repo_root)
    rules, rules_ref = _resolve_source(business_rules_source, repo_root)
    mapping, mapping_ref = _resolve_source(source_to_target_source, repo_root)
    return DocumentBundle(
        erd=erd,
        business_rules=rules,
        source_to_target=mapping,
        sources={
            "erd": erd_ref,
            "business_rules": rules_ref,
            "source_to_target": mapping_ref,
        },
    )


def read_s3_prefix(bucket: str, prefix: str) -> DocumentBundle:
    """Load the three canonical AbbVie ontology documents from an S3 prefix."""
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 required for S3 prefix reads") from exc

    client = boto3.client("s3")
    keys = {
        "erd": f"{prefix.rstrip('/')}/pharma_erd.md",
        "business_rules": f"{prefix.rstrip('/')}/business_rules.md",
        "source_to_target": f"{prefix.rstrip('/')}/source_to_target.csv",
    }
    contents: dict[str, str] = {}
    for kind, key in keys.items():
        obj = client.get_object(Bucket=bucket, Key=key)
        contents[kind] = obj["Body"].read().decode("utf-8")
    return DocumentBundle(
        erd=contents["erd"],
        business_rules=contents["business_rules"],
        source_to_target=contents["source_to_target"],
        sources={k: f"s3://{bucket}/{v}" for k, v in keys.items()},
    )
