"""Shared Snowflake connection helper for local dev and GitHub Actions OIDC."""

from __future__ import annotations

import os
from pathlib import Path


def connect(connection_name: str = "default"):
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
