"""Seed a handful of synthetic CRM accounts so the rest of the pipeline has data."""

from __future__ import annotations

import datetime as dt
import os
import uuid

import pymysql

SAMPLE = [
    ("AbbVie BioResearch", "pharma", 56_220_000_000, "[email protected]"),
    ("Allergan Aesthetics", "healthcare", 4_200_000_000, "[email protected]"),
    ("Pfizer Inc.", "pharma", 100_300_000_000, "[email protected]"),
    ("Genentech Labs", "biotech", 14_500_000_000, "[email protected]"),
    ("Optum Health", "healthcare", 226_700_000_000, "[email protected]"),
    ("Snowflake Inc.", "technology", 3_600_000_000, "[email protected]"),
    ("Databricks Inc.", "technology", 3_000_000_000, "[email protected]"),
]


def main() -> int:
    conn = pymysql.connect(
        host=os.environ["SUITECRM_DB_HOST"],
        port=int(os.environ.get("SUITECRM_DB_PORT", "3306")),
        user=os.environ["SUITECRM_DB_USER"],
        password=os.environ["SUITECRM_DB_PASSWORD"],
        database=os.environ["SUITECRM_DB_NAME"],
        autocommit=False,
    )
    now = dt.datetime.utcnow()
    try:
        with conn.cursor() as cur:
            for name, industry, revenue, email in SAMPLE:
                cur.execute(
                    "INSERT IGNORE INTO accounts "
                    "(id, name, industry, annual_revenue, email, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (str(uuid.uuid4()), name, industry, revenue, email, now, now),
                )
        conn.commit()
        print(f"seeded up to {len(SAMPLE)} accounts")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
