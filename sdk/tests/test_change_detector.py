from abbvie_dataops_governance.change_detector import detect


def test_app_only_change_is_not_data_change():
    d = detect(["README.md", "docs/some.md"])
    assert d.is_data_change is False
    assert d.triggered_manifests == []
    assert d.must_fail_closed is False


def test_snowflake_migration_triggers_manifest_and_blocks_without_schema():
    d = detect(["migrations/snowflake/V1.2.0__add_email.sql"])
    assert d.is_data_change is True
    assert "manifests/snowflake-curated.yaml" in d.triggered_manifests
    assert d.must_fail_closed is True
    assert any("manifests/schemas/snowflake/" in b for b in d.blockers)


def test_snowflake_migration_with_schema_passes():
    d = detect([
        "migrations/snowflake/V1.2.0__add_email.sql",
        "manifests/schemas/snowflake/accounts.json",
    ])
    assert d.is_data_change is True
    assert d.must_fail_closed is False


def test_suitecrm_change_triggers_its_manifest():
    d = detect([
        "apps/suitecrm/migrations/Version20260430000001.php",
        "manifests/schemas/suitecrm/accounts.json",
    ])
    assert d.is_data_change is True
    assert "manifests/suitecrm-crm.yaml" in d.triggered_manifests


def test_app_only_doc_does_not_trigger():
    d = detect(["docs/RUNBOOK.md", "README.md"])
    assert d.is_data_change is False


def test_ontology_doc_change_triggers_manifest():
    d = detect(["data/ontology/business_rules.md"])
    assert d.is_data_change is True
    assert "manifests/pharma-ontology.yaml" in d.triggered_manifests
    assert d.must_fail_closed is False
