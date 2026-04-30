"""Platform adapters: each implements `Adapter` so the SDK can introspect schema and pull DQ rows."""

from abbvie_dataops_governance.adapters.base import Adapter, AdapterResult

__all__ = ["Adapter", "AdapterResult"]


def get_adapter(name: str):
    if name == "snowflake":
        from abbvie_dataops_governance.adapters.snowflake import SnowflakeAdapter

        return SnowflakeAdapter
    if name == "emr":
        from abbvie_dataops_governance.adapters.emr import EMRAdapter

        return EMRAdapter
    if name == "suitecrm":
        from abbvie_dataops_governance.adapters.suitecrm import SuiteCRMAdapter

        return SuiteCRMAdapter
    raise ValueError(f"unknown adapter: {name}")
