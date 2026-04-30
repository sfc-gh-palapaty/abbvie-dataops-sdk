"""Snowflake adapter: reads INFORMATION_SCHEMA for actual columns + constraints.

Auth resolution order:
1. Existing snowflake-cli connection (env vars set by `snowflakedb/snowflake-cli-action`).
2. AWS Secrets Manager secret named in `manifest.connection.snowflake_account_secret`.
3. Plain env vars: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_AUTHENTICATOR`,
   and `SNOWFLAKE_PASSWORD` / `SNOWFLAKE_PRIVATE_KEY_RAW`.
"""

from __future__ import annotations

import json
import os
from typing import Any

from abbvie_dataops_governance.adapters.base import Adapter, AdapterResult


class SnowflakeAdapter(Adapter):
    name = "snowflake"

    def _connection_kwargs(self) -> dict[str, Any]:
        secret_id = self.manifest.connection.snowflake_account_secret
        if secret_id:
            try:
                import boto3

                client = boto3.client("secretsmanager")
                payload = json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])
            except Exception as e:
                raise RuntimeError(f"could not read Snowflake secret {secret_id}: {e}") from e
        else:
            payload = {}

        return {
            "account": payload.get("account") or os.environ.get("SNOWFLAKE_ACCOUNT", ""),
            "user": payload.get("user") or os.environ.get("SNOWFLAKE_USER", ""),
            "role": payload.get("role") or os.environ.get("SNOWFLAKE_ROLE"),
            "warehouse": payload.get("warehouse") or os.environ.get("SNOWFLAKE_WAREHOUSE"),
            "database": self.manifest.connection.snowflake_database
            or payload.get("database")
            or os.environ.get("SNOWFLAKE_DATABASE"),
            "schema": self.manifest.connection.snowflake_schema or os.environ.get("SNOWFLAKE_SCHEMA"),
            "authenticator": os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake_jwt"),
            "password": os.environ.get("SNOWFLAKE_PASSWORD"),
            "private_key": os.environ.get("SNOWFLAKE_PRIVATE_KEY_RAW"),
        }

    def introspect(self) -> AdapterResult:
        db = self.manifest.connection.snowflake_database
        sch = self.manifest.connection.snowflake_schema
        tbl = self.manifest.connection.snowflake_table
        if not (db and sch and tbl):
            return AdapterResult(facts={"note": "snowflake adapter missing db/schema/table — dry-run"})

        try:
            import snowflake.connector  # type: ignore[import-not-found]
        except ImportError:
            return AdapterResult(facts={"note": "snowflake-connector-python not installed — dry-run"})

        conn_kwargs = {k: v for k, v in self._connection_kwargs().items() if v is not None}
        try:
            conn = snowflake.connector.connect(**conn_kwargs)
        except Exception as e:
            return AdapterResult(facts={"note": f"snowflake connect failed — dry-run: {e}"})

        actual_columns: dict[str, str] = {}
        constraint_rows: list[dict[str, Any]] = []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_CATALOG = %s AND TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (db.upper(), sch.upper(), tbl.upper()),
            )
            for col, dtype in cur.fetchall():
                actual_columns[col] = dtype
            cur.execute(
                "SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE, TABLE_NAME "
                "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
                "WHERE TABLE_CATALOG = %s AND TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (db.upper(), sch.upper(), tbl.upper()),
            )
            for cn, ct, tn in cur.fetchall():
                constraint_rows.append({"constraint_name": cn, "constraint_type": ct, "table_name": tn})
        finally:
            conn.close()

        return AdapterResult(
            actual_columns=actual_columns,
            constraint_rows=constraint_rows,
            facts={"database": db, "schema": sch, "table": tbl},
        )
