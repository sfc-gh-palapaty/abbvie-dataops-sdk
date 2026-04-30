"""DataHub emitter — registers the dataset, schema, and upstream lineage via REST.

Uses the DataHub OpenAPI/Rest GMS endpoint directly (no `acryl-datahub` import
needed at runtime), so the SDK works on a slim CI runner. Set `DATAHUB_GMS_URL`
and optional `DATAHUB_TOKEN` env vars (or pass into the constructor).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from abbvie_dataops_governance.manifest import Manifest


def _aspect_envelope(urn: str, aspect_name: str, aspect_value: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal": {
            "entityType": "dataset",
            "entityUrn": urn,
            "changeType": "UPSERT",
            "aspectName": aspect_name,
            "aspect": {
                "contentType": "application/json",
                "value": json.dumps(aspect_value),
            },
        }
    }


def _schema_metadata(table_name: str, columns: dict[str, str], platform: str) -> dict[str, Any]:
    fields = []
    for col, dtype in columns.items():
        fields.append(
            {
                "fieldPath": col,
                "nullable": True,
                "type": {"type": {"com.linkedin.schema.StringType": {}}},
                "nativeDataType": dtype,
                "recursive": False,
            }
        )
    return {
        "schemaName": table_name,
        "platform": f"urn:li:dataPlatform:{platform}",
        "version": int(time.time()),
        "hash": "",
        "platformSchema": {"com.linkedin.schema.OtherSchema": {"rawSchema": ""}},
        "fields": fields,
    }


def _upstream_lineage(upstream_urns: list[str]) -> dict[str, Any]:
    return {
        "upstreams": [
            {"dataset": urn, "type": "TRANSFORMED", "auditStamp": {"time": int(time.time() * 1000), "actor": "urn:li:corpuser:abbvie-dataops"}}
            for urn in upstream_urns
        ]
    }


class DataHubEmitter:
    def __init__(self, gms_url: str | None = None, token: str | None = None):
        self.url = (gms_url or os.environ.get("DATAHUB_GMS_URL", "")).rstrip("/")
        self.token = token or os.environ.get("DATAHUB_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["Content-Type"] = "application/json"

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.url}/aspects?action=ingestProposal"
        try:
            resp = self.session.post(endpoint, data=json.dumps(body), timeout=20)
            resp.raise_for_status()
            return {"status": "sent", "endpoint": endpoint}
        except Exception as e:
            return {"status": "error", "endpoint": endpoint, "error": str(e)}

    def emit_dataset(
        self,
        manifest: Manifest,
        actual_columns: dict[str, str],
        owner_email: str | None = None,
    ) -> list[dict[str, Any]]:
        if not (self.enabled and manifest.emit.datahub):
            return []

        dh = manifest.emit.datahub
        results: list[dict[str, Any]] = []
        for ds in dh.datasets:
            urn = dh.dataset_urn_template.format(
                platform=dh.platform,
                env=dh.env,
                **ds,
            )
            table_name = ds.get("table", manifest.service)

            results.append(self._post(_aspect_envelope(urn, "schemaMetadata", _schema_metadata(table_name, actual_columns, dh.platform))))

            owners_aspect = {
                "owners": [
                    {"owner": f"urn:li:corpuser:{(owner_email or manifest.owners[0]).split('@')[0]}", "type": "DATAOWNER"}
                ],
                "lastModified": {"time": int(time.time() * 1000), "actor": "urn:li:corpuser:abbvie-dataops"},
            }
            results.append(self._post(_aspect_envelope(urn, "ownership", owners_aspect)))

            tags_aspect = {
                "tags": [
                    {"tag": f"urn:li:tag:classification:{manifest.classification}"},
                    {"tag": f"urn:li:tag:service:{manifest.service}"},
                ]
            }
            results.append(self._post(_aspect_envelope(urn, "globalTags", tags_aspect)))

            if dh.upstream_urns:
                results.append(self._post(_aspect_envelope(urn, "upstreamLineage", _upstream_lineage(dh.upstream_urns))))

        return results
