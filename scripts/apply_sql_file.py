#!/usr/bin/env python3
"""Execute a SQL file against Snowflake (local connections.toml or CI OIDC env vars)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from snowflake_connect import connect


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a SQL file on Snowflake")
    parser.add_argument("sql_file", type=Path)
    args = parser.parse_args()

    if not args.sql_file.exists():
        print(f"ERROR: {args.sql_file} not found", file=sys.stderr)
        return 1

    try:
        conn = connect()
    except Exception as exc:
        print(f"ERROR: Snowflake connection failed: {exc}", file=sys.stderr)
        return 1

    sql = args.sql_file.read_text(encoding="utf-8")
    print(f"Executing {args.sql_file.name}...")
    for cur in conn.execute_string(sql):
        try:
            rows = cur.fetchall()
            if rows:
                print(f"  {rows[0]}")
        except Exception:
            pass
    conn.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
