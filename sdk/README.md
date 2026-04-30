# abbvie-dataops-governance-sdk

Manifest-driven DataOps governance SDK for the AbbVie PoC. One library, one CLI, one
manifest format — invoked the same way from any pipeline (Snowflake, EMR Serverless,
SuiteCRM app) so governance is **consistent and auditable** across data planes.

## Install

```bash
pip install -e '.[all]'
```

## Use

```bash
abbvie-dataops run \
  --manifest ../manifests/snowflake-curated.yaml \
  --profile promote \
  --evidence-out ./evidence.json
```

Exit code is non-zero if any required check fails. The evidence bundle is written
to `--evidence-out` (uploaded as a CI artifact) and lineage events flow to
OpenLineage / Marquez and DataHub via the configured emitters.

## What it checks

| Module | Purpose |
|---|---|
| `schema_enforcement` | Compares expected columns / types to the deployed table |
| `data_quality` | Declarative DQ checks (row count, nulls, uniqueness, SQL assert) |
| `constraints` | PK / FK / unique / not-null contracts vs INFORMATION_SCHEMA |
| `tokenization` | Static review of sensitivity classification vs masking method |
| `change_detector` | Path-based "data change gate" for PR governance workflow |

## What it emits

| Emitter | Target |
|---|---|
| `openlineage` | Marquez backend on the DataHub EC2 (`OPENLINEAGE_URL`) |
| `datahub` | DataHub GMS REST (`DATAHUB_GMS_URL`) — datasets + schema + lineage |

See `manifests/*.yaml` in the repo root for working examples.
