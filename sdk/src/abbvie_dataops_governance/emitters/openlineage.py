"""OpenLineage emitter — sends START/COMPLETE/FAIL run events to a Marquez backend.

We talk the OpenLineage HTTP wire protocol directly (no openlineage-python dep
required) so the SDK stays light. The endpoint is `POST {OPENLINEAGE_URL}/api/v1/lineage`.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import Any

import requests

from abbvie_dataops_governance.manifest import Manifest

PRODUCER = "https://github.com/sfc-gh-palapaty/abbvie-dataops-poc-aws"
SCHEMA_URL = "https://openlineage.io/spec/1-0-5/OpenLineage.json#/definitions/RunEvent"


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _dataset(namespace: str, name: str, columns: dict[str, str] | None = None) -> dict[str, Any]:
    facets: dict[str, Any] = {}
    if columns:
        facets["schema"] = {
            "_producer": PRODUCER,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
            "fields": [{"name": k, "type": v} for k, v in columns.items()],
        }
    return {"namespace": namespace, "name": name, "facets": facets}


class OpenLineageEmitter:
    def __init__(self, url: str | None = None, api_key: str | None = None):
        self.url = (url or os.environ.get("OPENLINEAGE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENLINEAGE_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        self.session.headers["Content-Type"] = "application/json"

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def emit_run(
        self,
        manifest: Manifest,
        event_type: str,
        run_id: str,
        actual_columns: dict[str, str] | None = None,
        extra_facets: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not (self.enabled and manifest.emit.openlineage):
            return None

        ol = manifest.emit.openlineage
        inputs = [_dataset(ol.namespace, name) for name in ol.inputs]
        outputs = [_dataset(ol.namespace, name, columns=actual_columns) for name in ol.outputs] or [
            _dataset(ol.namespace, ol.job, columns=actual_columns)
        ]
        body = {
            "eventType": event_type,
            "eventTime": _now_iso(),
            "producer": PRODUCER,
            "schemaURL": SCHEMA_URL,
            "run": {"runId": run_id, "facets": {**(extra_facets or {})}},
            "job": {"namespace": ol.namespace, "name": ol.job},
            "inputs": inputs,
            "outputs": outputs,
        }

        endpoint = f"{self.url}/api/v1/lineage"
        try:
            resp = self.session.post(endpoint, data=json.dumps(body), timeout=15)
            resp.raise_for_status()
            return {"status": "sent", "endpoint": endpoint, "event_type": event_type}
        except Exception as e:
            return {"status": "error", "endpoint": endpoint, "event_type": event_type, "error": str(e)}

    @staticmethod
    def new_run_id() -> str:
        return str(uuid.uuid4())
