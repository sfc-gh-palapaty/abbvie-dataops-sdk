"""EMR / Glue adapter: reads Iceberg / Glue Data Catalog metadata for the deployed table."""

from __future__ import annotations

from typing import Any

from abbvie_dataops_governance.adapters.base import Adapter, AdapterResult


class EMRAdapter(Adapter):
    name = "emr"

    def introspect(self) -> AdapterResult:
        db = self.manifest.connection.glue_database
        tbl = self.manifest.connection.glue_table
        if not (db and tbl):
            return AdapterResult(facts={"note": "emr adapter missing glue_database/glue_table — dry-run"})

        try:
            import boto3
        except ImportError:
            return AdapterResult(facts={"note": "boto3 not installed — dry-run"})

        client = boto3.client("glue")
        try:
            resp = client.get_table(DatabaseName=db, Name=tbl)
        except client.exceptions.EntityNotFoundException:
            return AdapterResult(facts={"note": f"glue table {db}.{tbl} not found — first deploy"})
        except Exception as e:
            return AdapterResult(facts={"note": f"glue lookup failed — dry-run: {e}"})

        cols: dict[str, str] = {}
        sd = resp["Table"].get("StorageDescriptor", {})
        for c in sd.get("Columns", []):
            cols[c["Name"]] = c.get("Type", "")
        partition_keys = [c["Name"] for c in resp["Table"].get("PartitionKeys", [])]

        facts: dict[str, Any] = {
            "database": db,
            "table": tbl,
            "location": sd.get("Location"),
            "input_format": sd.get("InputFormat"),
            "partition_keys": partition_keys,
            "table_type": resp["Table"].get("TableType"),
            "parameters": resp["Table"].get("Parameters", {}),
        }
        return AdapterResult(actual_columns=cols, facts=facts)
