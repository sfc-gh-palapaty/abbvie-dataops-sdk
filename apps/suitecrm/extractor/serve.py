"""Tiny FastAPI surface that mimics the SuiteCRM REST API used by downstream apps.

This is just enough to give the PoC a 'living' app endpoint to wire dashboards or
other consumers against; the governed data path (extractor + Iceberg + Snowflake)
remains the canonical one.
"""

from __future__ import annotations

import os

import pymysql
from fastapi import FastAPI, HTTPException

app = FastAPI(title="SuiteCRM PoC", version="0.1.0")


def _conn():
    return pymysql.connect(
        host=os.environ["SUITECRM_DB_HOST"],
        port=int(os.environ.get("SUITECRM_DB_PORT", "3306")),
        user=os.environ["SUITECRM_DB_USER"],
        password=os.environ["SUITECRM_DB_PASSWORD"],
        database=os.environ["SUITECRM_DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor,
    )


@app.get("/healthz")
def healthz() -> dict:
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(503, str(e))


@app.get("/api/v8/modules/Accounts")
def list_accounts(limit: int = 25) -> dict:
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT * FROM accounts LIMIT %s", (limit,))
        rows = cur.fetchall()
    return {"data": rows, "meta": {"count": len(rows)}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
