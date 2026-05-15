"""Seed the AbbVie DataOps PoC demo lineage end-to-end.

This drives the live Marquez (OpenLineage backend) + DataHub GMS endpoints
exposed by the EC2 to publish a complete cross-platform lineage chain so that
the walkthrough shows real edges in both UIs:

    SuiteCRM (mysql)
        suitecrm.public.accounts
            -> suitecrm.accounts.snapshot
    S3 raw landing zone (s3)
        abbvie-dataops-poc-raw/suitecrm/accounts
            -> suitecrm.accounts.land_to_s3
    Glue / Iceberg curated (glue)
        abbvie_dataops_poc_curated.accounts
            -> emr.curated.accounts.transform
    Snowflake curated (snowflake)
        abbvie_dataops_dev.curated.accounts
            -> snowflake.curated.accounts.upsert
    Snowflake governance view (snowflake)
        abbvie_dataops_dev.curated.v_accounts_governed
            -> snowflake.curated.v_accounts_governed.refresh

Run from the repo root with the live endpoints exported:

    OPENLINEAGE_URL=http://34.205.77.61:5000 \
    DATAHUB_GMS_URL=http://34.205.77.61:8000 \
    python customer/seed_demo_lineage.py

Idempotent: re-runs append fresh COMPLETE runs, which is what the timeline UI shows.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import uuid
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
OL_URL = os.environ.get("OPENLINEAGE_URL", "http://34.205.77.61:5000").rstrip("/")
DH_URL = os.environ.get("DATAHUB_GMS_URL", "http://34.205.77.61:8000").rstrip("/")
PRODUCER = "https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk"
SCHEMA_URL = "https://openlineage.io/spec/1-0-5/OpenLineage.json#/definitions/RunEvent"

# ---------------------------------------------------------------------------
# Schemas (column name -> native type) per dataset.
# Kept identical across the chain so column-level lineage will resolve.
# ---------------------------------------------------------------------------
ACCOUNT_COLS_MYSQL: dict[str, str] = {
    "id": "VARCHAR(36)",
    "name": "VARCHAR(255)",
    "industry": "VARCHAR(64)",
    "annual_revenue": "DECIMAL(18,2)",
    "email": "VARCHAR(255)",
    "phone": "VARCHAR(64)",
    "website": "VARCHAR(255)",
    "date_entered": "DATETIME",
    "date_modified": "DATETIME",
}
ACCOUNT_COLS_PARQUET: dict[str, str] = {
    "id": "string",
    "name": "string",
    "industry": "string",
    "annual_revenue": "decimal(18,2)",
    "email": "string",
    "phone": "string",
    "website": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp",
}
ACCOUNT_COLS_ICEBERG: dict[str, str] = {**ACCOUNT_COLS_PARQUET, "ingest_run_id": "string"}
ACCOUNT_COLS_SNOWFLAKE: dict[str, str] = {
    "ID": "VARCHAR",
    "NAME": "VARCHAR",
    "INDUSTRY": "VARCHAR",
    "ANNUAL_REVENUE": "NUMBER(18,2)",
    "EMAIL": "VARCHAR",
    "PHONE": "VARCHAR",
    "WEBSITE": "VARCHAR",
    "CREATED_AT": "TIMESTAMP_NTZ",
    "UPDATED_AT": "TIMESTAMP_NTZ",
}
VIEW_COLS_SNOWFLAKE: dict[str, str] = {
    "ID": "VARCHAR",
    "NAME": "VARCHAR",
    "INDUSTRY": "VARCHAR",
    "ANNUAL_REVENUE_BUCKETED": "VARCHAR",
    "EMAIL_TOKENIZED": "VARCHAR",
    "PHONE_TOKENIZED": "VARCHAR",
    "WEBSITE_DOMAIN_ONLY": "VARCHAR",
    "UPDATED_AT": "TIMESTAMP_NTZ",
}

# ---------------------------------------------------------------------------
# Datasets across platforms. Marquez stores OL identity (namespace, name).
# DataHub stores `urn:li:dataset:(...)`. We register both for every node.
# ---------------------------------------------------------------------------
DATASETS: list[dict[str, Any]] = [
    {
        "id": "suitecrm_accounts",
        "ol_namespace": "abbvie.suitecrm",
        "ol_name": "suitecrm.public.accounts",
        "dh_platform": "mysql",
        "dh_name": "suitecrm.public.accounts",
        "columns": ACCOUNT_COLS_MYSQL,
        "owner": "crm-platform",
        "tags": ["classification:confidential", "service:suitecrm-crm-accounts", "source-of-truth"],
        "description": "SuiteCRM Accounts table on RDS MySQL. Source of truth for CRM accounts.",
    },
    {
        "id": "s3_raw_accounts",
        "ol_namespace": "abbvie.s3",
        "ol_name": "abbvie-dataops-poc-raw/suitecrm/accounts",
        "dh_platform": "s3",
        "dh_name": "abbvie-dataops-poc-raw-194722405805/suitecrm/accounts",
        "columns": ACCOUNT_COLS_PARQUET,
        "owner": "data-platform",
        "tags": ["classification:confidential", "service:suitecrm-extractor", "zone:raw"],
        "description": "Raw landing zone (Parquet) written by the SuiteCRM extractor before EMR transforms.",
    },
    {
        "id": "glue_curated_accounts",
        "ol_namespace": "abbvie.glue",
        "ol_name": "abbvie_dataops_poc_curated.accounts",
        "dh_platform": "glue",
        "dh_name": "abbvie_dataops_poc_curated.accounts",
        "columns": ACCOUNT_COLS_ICEBERG,
        "owner": "data-platform",
        "tags": ["classification:confidential", "service:emr-curated-accounts", "format:iceberg", "zone:curated"],
        "description": "Curated Iceberg ACCOUNTS table built by EMR Serverless from the raw zone. Glue Data Catalog managed.",
    },
    {
        "id": "snowflake_accounts",
        "ol_namespace": "abbvie.snowflake",
        "ol_name": "abbvie_dataops_dev.curated.accounts",
        "dh_platform": "snowflake",
        "dh_name": "abbvie_dataops_dev.curated.accounts",
        "columns": ACCOUNT_COLS_SNOWFLAKE,
        "owner": "data-platform",
        "tags": ["classification:confidential", "service:snowflake-curated-accounts", "zone:curated"],
        "description": "Snowflake-side analytics-ready ACCOUNTS table promoted from Glue/Iceberg by the snowflake-deploy workflow.",
    },
    {
        "id": "snowflake_view_governed",
        "ol_namespace": "abbvie.snowflake",
        "ol_name": "abbvie_dataops_dev.curated.v_accounts_governed",
        "dh_platform": "snowflake",
        "dh_name": "abbvie_dataops_dev.curated.v_accounts_governed",
        "columns": VIEW_COLS_SNOWFLAKE,
        "owner": "data-governance",
        "tags": ["classification:internal", "service:snowflake-curated-accounts", "zone:consumption", "tokenized"],
        "description": "Governance overlay view: tokenizes EMAIL/PHONE and buckets ANNUAL_REVENUE per the tokenization policy. Safe for downstream BI.",
    },
]

DATASET_BY_ID: dict[str, dict[str, Any]] = {d["id"]: d for d in DATASETS}

# Job definition: each one connects upstream datasets to a single downstream.
JOBS: list[dict[str, Any]] = [
    {
        "ol_namespace": "abbvie.suitecrm",
        "ol_job": "suitecrm.accounts.snapshot",
        "inputs": [],
        "outputs": ["suitecrm_accounts"],
        "description": "SuiteCRM application writes/updates Accounts (the CRM source of truth).",
    },
    {
        "ol_namespace": "abbvie.s3",
        "ol_job": "suitecrm.accounts.land_to_s3",
        "inputs": ["suitecrm_accounts"],
        "outputs": ["s3_raw_accounts"],
        "description": "SuiteCRM extractor (FastAPI app on ECS) snapshots Accounts to S3 as Parquet.",
    },
    {
        "ol_namespace": "abbvie.glue",
        "ol_job": "emr.curated.accounts.transform",
        "inputs": ["s3_raw_accounts"],
        "outputs": ["glue_curated_accounts"],
        "description": "EMR Serverless PySpark job reads Parquet, normalizes, writes Iceberg into Glue Catalog.",
    },
    {
        "ol_namespace": "abbvie.snowflake",
        "ol_job": "snowflake.curated.accounts.upsert",
        "inputs": ["glue_curated_accounts"],
        "outputs": ["snowflake_accounts"],
        "description": "schemachange + SDK promote the Iceberg table into Snowflake CURATED.ACCOUNTS.",
    },
    {
        "ol_namespace": "abbvie.snowflake",
        "ol_job": "snowflake.curated.v_accounts_governed.refresh",
        "inputs": ["snowflake_accounts"],
        "outputs": ["snowflake_view_governed"],
        "description": "Repeatable schemachange script materializes the governance overlay view (tokenization + bucketing).",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _ds_urn(ds: dict[str, Any]) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{ds['dh_platform']},{ds['dh_name']},PROD)"


def _ol_dataset(ds: dict[str, Any], with_schema: bool = True) -> dict[str, Any]:
    facets: dict[str, Any] = {}
    if with_schema:
        facets["schema"] = {
            "_producer": PRODUCER,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
            "fields": [{"name": k, "type": v} for k, v in ds["columns"].items()],
        }
        facets["dataSource"] = {
            "_producer": PRODUCER,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
            "name": ds["dh_platform"],
            "uri": ds["dh_name"],
        }
        facets["documentation"] = {
            "_producer": PRODUCER,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationDatasetFacet.json",
            "description": ds["description"],
        }
    return {"namespace": ds["ol_namespace"], "name": ds["ol_name"], "facets": facets}


def _post(url: str, body: dict[str, Any]) -> tuple[int, str]:
    try:
        resp = requests.post(url, data=json.dumps(body), headers={"Content-Type": "application/json"}, timeout=20)
        return resp.status_code, resp.text[:200]
    except Exception as e:  # pragma: no cover
        return 0, str(e)


# ---------------------------------------------------------------------------
# Marquez / OpenLineage
# ---------------------------------------------------------------------------
def emit_openlineage_run(job: dict[str, Any]) -> str:
    run_id = str(uuid.uuid4())
    inputs = [_ol_dataset(DATASET_BY_ID[i]) for i in job["inputs"]]
    outputs = [_ol_dataset(DATASET_BY_ID[o]) for o in job["outputs"]]

    common: dict[str, Any] = {
        "producer": PRODUCER,
        "schemaURL": SCHEMA_URL,
        "run": {
            "runId": run_id,
            "facets": {
                "nominalTime": {
                    "_producer": PRODUCER,
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/NominalTimeRunFacet.json",
                    "nominalStartTime": _now(),
                }
            },
        },
        "job": {
            "namespace": job["ol_namespace"],
            "name": job["ol_job"],
            "facets": {
                "documentation": {
                    "_producer": PRODUCER,
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationJobFacet.json",
                    "description": job["description"],
                }
            },
        },
        "inputs": inputs,
        "outputs": outputs,
    }

    start_status, _ = _post(f"{OL_URL}/api/v1/lineage", {**common, "eventType": "START", "eventTime": _now()})
    time.sleep(0.2)
    end_status, _ = _post(f"{OL_URL}/api/v1/lineage", {**common, "eventType": "COMPLETE", "eventTime": _now()})
    print(f"  [marquez] {job['ol_namespace']}/{job['ol_job']:<48s} START={start_status} COMPLETE={end_status} run={run_id[:8]}")
    return run_id


# ---------------------------------------------------------------------------
# DataHub aspects
# ---------------------------------------------------------------------------
def _dh_envelope(urn: str, aspect_name: str, value: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal": {
            "entityType": "dataset",
            "entityUrn": urn,
            "changeType": "UPSERT",
            "aspectName": aspect_name,
            "aspect": {"contentType": "application/json", "value": json.dumps(value)},
        }
    }


def _dh_post(body: dict[str, Any]) -> int:
    status, _ = _post(f"{DH_URL}/aspects?action=ingestProposal", body)
    return status


def _dh_schema(table_name: str, columns: dict[str, str], platform: str) -> dict[str, Any]:
    return {
        "schemaName": table_name,
        "platform": f"urn:li:dataPlatform:{platform}",
        "version": int(time.time()),
        "hash": "",
        "platformSchema": {"com.linkedin.schema.OtherSchema": {"rawSchema": ""}},
        "fields": [
            {
                "fieldPath": col,
                "nullable": True,
                "type": {"type": {"com.linkedin.schema.StringType": {}}},
                "nativeDataType": dtype,
                "recursive": False,
            }
            for col, dtype in columns.items()
        ],
    }


def emit_datahub_dataset(ds: dict[str, Any], upstream_urns: list[str]) -> None:
    urn = _ds_urn(ds)

    # NOTE: datasetProperties.uri is typed as a strict java.net.URI in the
    # DataHub PDL schema. If we set it to an unqualified table name like
    # `abbvie_dataops_poc_curated.accounts` GMS deserialization later crashes
    # with TemplateOutputCastException, and the GraphQL searchAcrossEntities
    # batch loader fails, blanking the search results UI. Omit `uri` and use
    # `customProperties` instead.
    statuses = [
        _dh_post(_dh_envelope(urn, "datasetProperties", {
            "description": ds["description"],
            "customProperties": {
                "ol_namespace": ds["ol_namespace"],
                "ol_name": ds["ol_name"],
                "platform": ds["dh_platform"],
                "physical_name": ds["dh_name"],
            },
            "tags": [],
        })),
        _dh_post(_dh_envelope(urn, "schemaMetadata", _dh_schema(ds["dh_name"], ds["columns"], ds["dh_platform"]))),
        _dh_post(_dh_envelope(urn, "ownership", {
            "owners": [{"owner": f"urn:li:corpuser:{ds['owner']}", "type": "DATAOWNER"}],
            "lastModified": {"time": int(time.time() * 1000), "actor": "urn:li:corpuser:abbvie-dataops"},
        })),
        _dh_post(_dh_envelope(urn, "globalTags", {
            "tags": [{"tag": f"urn:li:tag:{t}"} for t in ds["tags"]],
        })),
    ]
    if upstream_urns:
        statuses.append(_dh_post(_dh_envelope(urn, "upstreamLineage", {
            "upstreams": [
                {
                    "dataset": u,
                    "type": "TRANSFORMED",
                    "auditStamp": {"time": int(time.time() * 1000), "actor": "urn:li:corpuser:abbvie-dataops"},
                }
                for u in upstream_urns
            ]
        })))
    summary = ",".join(str(s) for s in statuses)
    print(f"  [datahub] {ds['dh_platform']:>10s} :: {ds['dh_name']:<60s} aspects={summary}")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"OpenLineage URL: {OL_URL}")
    print(f"DataHub GMS URL: {DH_URL}")

    # 1) Compute upstream URNs per dataset (derived from JOBS chain).
    upstreams_by_ds: dict[str, list[str]] = {d["id"]: [] for d in DATASETS}
    for job in JOBS:
        for out_id in job["outputs"]:
            for in_id in job["inputs"]:
                up = _ds_urn(DATASET_BY_ID[in_id])
                if up not in upstreams_by_ds[out_id]:
                    upstreams_by_ds[out_id].append(up)

    # 2) Push DataHub datasets first so the search index has them; lineage edges
    #    come along on the same envelope.
    print("\n=== DataHub aspects ===")
    for ds in DATASETS:
        emit_datahub_dataset(ds, upstreams_by_ds[ds["id"]])

    # 3) Push OpenLineage START/COMPLETE for each job in pipeline order.
    print("\n=== Marquez (OpenLineage) runs ===")
    for job in JOBS:
        emit_openlineage_run(job)

    print("\nDone. Browse:")
    print(f"  Marquez UI : http://34.205.77.61:13000  (namespaces: abbvie.suitecrm, abbvie.s3, abbvie.glue, abbvie.snowflake)")
    print(f"  DataHub UI : http://34.205.77.61:9002  (search: 'accounts' across mysql/s3/glue/snowflake platforms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
