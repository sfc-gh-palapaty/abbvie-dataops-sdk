from abbvie_dataops_governance.schema_enforcement import ExpectedColumn, SchemaEnforcer


def test_no_drift():
    enforcer = SchemaEnforcer({"id": "VARCHAR", "ts": "TIMESTAMP_NTZ"})
    drift = enforcer.diff([
        ExpectedColumn("id", "VARCHAR"),
        ExpectedColumn("ts", "TIMESTAMP_NTZ"),
    ])
    assert not drift.is_drift


def test_missing_column():
    enforcer = SchemaEnforcer({"id": "VARCHAR"})
    drift = enforcer.diff([ExpectedColumn("id", "VARCHAR"), ExpectedColumn("email", "VARCHAR")])
    assert drift.missing == ["email"]
    assert drift.is_drift


def test_type_mismatch_raises_on_enforce():
    enforcer = SchemaEnforcer({"id": "NUMBER"})
    import pytest

    with pytest.raises(ValueError, match="schema drift"):
        enforcer.enforce([ExpectedColumn("id", "VARCHAR")])
