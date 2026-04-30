from pathlib import Path

import yaml

from abbvie_dataops_governance.manifest import Manifest, load_manifest


def _write_manifest(tmp_path: Path) -> Path:
    payload = {
        "service": "suitecrm-crm",
        "owners": ["crm@abbvie.com"],
        "classification": "confidential",
        "adapter": "suitecrm",
        "profile": "build",
        "connection": {"suitecrm_db_secret_arn": "arn:placeholder", "suitecrm_table": "accounts"},
        "checks": {
            "schema_enforcement": {"expected": "schemas/suitecrm/accounts.json"},
            "data_quality": {"suite": "ge_suites/accounts.yaml"},
        },
        "emit": {
            "datahub": {"platform": "suitecrm", "env": "PROD", "datasets": [{"db": "suitecrm", "schema": "public", "table": "accounts"}]},
            "openlineage": {"namespace": "abbvie.crm", "job": "suitecrm.accounts"},
        },
    }
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return p


def test_load_manifest_round_trip(tmp_path):
    m = load_manifest(_write_manifest(tmp_path))
    assert isinstance(m, Manifest)
    assert m.adapter == "suitecrm"
    assert m.checks.schema_enforcement is not None
    assert m.emit.datahub.platform == "suitecrm"


def test_owners_required(tmp_path):
    payload = {"service": "x", "owners": [], "adapter": "snowflake"}
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(payload), encoding="utf-8")
    import pytest

    with pytest.raises(Exception):
        load_manifest(p)
