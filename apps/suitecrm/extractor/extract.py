"""Read SuiteCRM `accounts` rows -> Parquet -> S3 raw bucket.

Emits one OpenLineage event for the extract job so the lineage chain starts here.
"""

from __future__ import annotations

import datetime as dt
import io
import os
import sys
import uuid
from pathlib import PurePosixPath

import boto3
import click
import pandas as pd
import pymysql
import requests


def _env_or_die(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"missing env var: {key}", file=sys.stderr)
        sys.exit(2)
    return val


def _emit_lineage(rows: int, s3_uri: str, table: str) -> None:
    url = os.environ.get("OPENLINEAGE_URL")
    if not url:
        return
    namespace = "abbvie.suitecrm"
    body = {
        "eventType": "COMPLETE",
        "eventTime": dt.datetime.utcnow().isoformat() + "Z",
        "producer": "suitecrm-extractor",
        "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/definitions/RunEvent",
        "run": {"runId": str(uuid.uuid4())},
        "job": {"namespace": namespace, "name": f"suitecrm.public.{table}.snapshot"},
        "inputs": [{"namespace": namespace, "name": f"suitecrm.public.{table}"}],
        "outputs": [{"namespace": "s3", "name": s3_uri.replace("s3://", "")}],
    }
    try:
        requests.post(f"{url.rstrip('/')}/api/v1/lineage", json=body, timeout=10)
    except Exception as e:  # best-effort
        print(f"openlineage emit failed: {e}", file=sys.stderr)


@click.command()
@click.option("--table", default="accounts", show_default=True)
@click.option("--s3-uri", required=True, help="s3://bucket/prefix/")
def main(table: str, s3_uri: str) -> None:
    conn = pymysql.connect(
        host=_env_or_die("SUITECRM_DB_HOST"),
        port=int(os.environ.get("SUITECRM_DB_PORT", "3306")),
        user=_env_or_die("SUITECRM_DB_USER"),
        password=_env_or_die("SUITECRM_DB_PASSWORD"),
        database=_env_or_die("SUITECRM_DB_NAME"),
    )
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
    finally:
        conn.close()

    print(f"extracted {len(df)} rows from {table}")

    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=False)
    buf.seek(0)

    parsed = s3_uri.replace("s3://", "")
    bucket = parsed.split("/", 1)[0]
    prefix = parsed.split("/", 1)[1] if "/" in parsed else ""
    key = str(PurePosixPath(prefix) / f"{table}-{dt.datetime.utcnow():%Y%m%dT%H%M%S}.parquet")

    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    final_uri = f"s3://{bucket}/{key}"
    print(f"wrote {final_uri}")

    _emit_lineage(len(df), final_uri, table)


if __name__ == "__main__":
    main()
