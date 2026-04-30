"""Tiny migration runner: applies SQL files in apps/suitecrm/migrations/Version*.sql in order.

Tracks applied migrations in a `schema_migrations` table.  Idempotent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymysql


def _ensure_tracking(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version VARCHAR(255) NOT NULL PRIMARY KEY,
              applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    conn.commit()


def _applied(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def _apply(conn, version: str, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)
        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
    conn.commit()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--migrations-dir", required=True, type=Path)
    args = p.parse_args()

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        autocommit=False,
    )
    try:
        _ensure_tracking(conn)
        applied = _applied(conn)
        files = sorted(args.migrations_dir.glob("Version*.sql"))
        for f in files:
            version = f.stem.split("__", 1)[0]
            if version in applied:
                print(f"[skip ] {version}")
                continue
            print(f"[apply] {version}: {f.name}")
            _apply(conn, version, f)
        print("done")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
