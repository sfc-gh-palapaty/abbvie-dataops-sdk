"""SuiteCRM adapter: reads MySQL INFORMATION_SCHEMA via the secret stored in AWS Secrets Manager."""

from __future__ import annotations

import json
from typing import Any

from abbvie_dataops_governance.adapters.base import Adapter, AdapterResult


class SuiteCRMAdapter(Adapter):
    name = "suitecrm"

    def _conn_info(self) -> dict[str, Any]:
        secret_id = self.manifest.connection.suitecrm_db_secret_arn
        if not secret_id:
            return {}
        try:
            import boto3

            client = boto3.client("secretsmanager")
            return json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
        except Exception:
            return {}

    def introspect(self) -> AdapterResult:
        info = self._conn_info()
        tbl = self.manifest.connection.suitecrm_table
        if not (info and tbl):
            return AdapterResult(facts={"note": "suitecrm adapter missing secret/table — dry-run"})

        try:
            import pymysql  # type: ignore[import-not-found]
        except ImportError:
            return AdapterResult(facts={"note": "pymysql not installed — dry-run"})

        try:
            conn = pymysql.connect(
                host=info["host"],
                port=int(info.get("port", 3306)),
                user=info["username"],
                password=info["password"],
                database=info["database"],
                connect_timeout=10,
            )
        except Exception as e:
            return AdapterResult(facts={"note": f"mysql connect failed — dry-run: {e}"})

        actual_columns: dict[str, str] = {}
        constraint_rows: list[dict[str, Any]] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (info["database"], tbl),
                )
                for col, dtype in cur.fetchall():
                    actual_columns[col] = dtype
                cur.execute(
                    "SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE, TABLE_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                    (info["database"], tbl),
                )
                for cn, ct, tn in cur.fetchall():
                    constraint_rows.append({"constraint_name": cn, "constraint_type": ct, "table_name": tn})
        finally:
            conn.close()

        return AdapterResult(
            actual_columns=actual_columns,
            constraint_rows=constraint_rows,
            facts={"database": info["database"], "table": tbl, "host": info["host"]},
        )
