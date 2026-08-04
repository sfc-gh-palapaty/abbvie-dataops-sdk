#!/usr/bin/env python3
"""Import OSI YAML into Snowflake semantic view and run verification queries."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _connect(connection_name: str = "default"):
    import snowflake.connector

    if os.getenv("SNOWFLAKE_ACCOUNT"):
        kwargs: dict = {
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "user": os.environ["SNOWFLAKE_USER"],
            "role": os.environ.get("SNOWFLAKE_ROLE"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
            "database": os.environ.get("SNOWFLAKE_DATABASE"),
        }
        if os.getenv("SNOWFLAKE_AUTHENTICATOR", "").upper() == "WORKLOAD_IDENTITY":
            kwargs["authenticator"] = "WORKLOAD_IDENTITY"
            if os.getenv("SNOWFLAKE_TOKEN"):
                kwargs["token"] = os.environ["SNOWFLAKE_TOKEN"]
            if os.getenv("SNOWFLAKE_WORKLOAD_IDENTITY_PROVIDER"):
                kwargs["workload_identity_provider"] = os.environ["SNOWFLAKE_WORKLOAD_IDENTITY_PROVIDER"]
        elif os.getenv("SNOWFLAKE_PASSWORD"):
            kwargs["password"] = os.environ["SNOWFLAKE_PASSWORD"]
        return snowflake.connector.connect(**kwargs)

    import tomllib

    conn_file = Path.home() / ".snowflake" / "connections.toml"
    cfg = tomllib.loads(conn_file.read_text())
    name = cfg.get("default_connection_name", connection_name)
    c = cfg[name]
    return snowflake.connector.connect(
        account=c["account"],
        user=c["user"],
        password=c.get("password"),
        role=c.get("role", "ACCOUNTADMIN"),
        warehouse=c.get("warehouse"),
        database=c.get("database"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Import OSI YAML to Snowflake semantic view")
    parser.add_argument(
        "--yaml",
        default="outputs/ontology/abbvie_pharma_intelligence_v2.1.0.yaml",
        help="Path to OSI YAML file",
    )
    parser.add_argument("--schema", default="ABBVIE_DATAOPS_DEV.CURATED")
    parser.add_argument("--connection", default="default")
    args = parser.parse_args()

    yaml_path = Path(args.yaml)
    if not yaml_path.exists():
        print(f"ERROR: {yaml_path} not found", file=sys.stderr)
        return 1

    yaml_content = yaml_path.read_text(encoding="utf-8")

    try:
        conn = _connect(args.connection)
    except ImportError:
        print("ERROR: pip install snowflake-connector-python", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Snowflake connection failed: {exc}", file=sys.stderr)
        return 1

    cur = conn.cursor()
    cur.execute(f"USE SCHEMA {args.schema}")

    print(f"Creating semantic view in {args.schema} from {yaml_path.name}...")
    # Use dollar-quoting — no need to escape single quotes inside YAML
    cur.execute(
        f"CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML('{args.schema}', $${yaml_content}$$)"
    )
    result = cur.fetchone()
    print(f"  Result: {result}")

    view_fqn = f"{args.schema}.ABBVIE_PHARMA_INTELLIGENCE"
    print(f"\nVerifying semantic view exists...")
    cur.execute(f"SHOW SEMANTIC VIEWS LIKE 'ABBVIE_PHARMA_INTELLIGENCE' IN SCHEMA {args.schema}")
    rows = cur.fetchall()
    print(f"  Found {len(rows)} semantic view(s)")

    print(f"\nRound-trip OSI export (first 500 chars)...")
    cur.execute(f"SELECT SYSTEM$READ_OSSIE_YAML_FROM_SEMANTIC_VIEW('{view_fqn}')")
    exported = cur.fetchone()[0]
    print(exported[:500] + "...")

    print(f"\nQuery: total prescriptions metric")
    cur.execute(
        f"""
        SELECT * FROM SEMANTIC_VIEW(
            {view_fqn.split('.')[-1]}
            METRICS total_prescriptions
        )
        """
    )
    metric_row = cur.fetchone()
    print(f"  total_prescriptions = {metric_row}")

    print(f"\nQuery: prescription dimensions")
    cur.execute(
        f"""
        SELECT * FROM SEMANTIC_VIEW(
            {view_fqn.split('.')[-1]}
            DIMENSIONS prescriptions.patient_id, prescriptions.drug_id,
                       prescriptions.switch_reason
            METRICS total_prescriptions
        )
        """
    )
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"  Columns: {cols}")
    for row in rows:
        print(f"    {row}")

    print(f"\nQuery: switch prescriptions metric")
    cur.execute(
        f"""
        SELECT * FROM SEMANTIC_VIEW(
            {view_fqn.split('.')[-1]}
            METRICS switch_prescriptions, patients_on_therapy
        )
        """
    )
    print(f"  metrics = {cur.fetchone()}")

    print(f"\nQuery: KOL prescriber count metric")
    cur.execute(
        f"""
        SELECT * FROM SEMANTIC_VIEW(
            {view_fqn.split('.')[-1]}
            DIMENSIONS prescribers.is_kol, prescribers.specialty
            METRICS kol_prescriber_count
        )
        """
    )
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        print(f"    {dict(zip(cols, row))}")

    cur.close()
    conn.close()
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
