# AbbVie DataOps SDK — Proof of Concept

A working proof-of-concept for a **manifest-driven DataOps Governance SDK** that any AbbVie pipeline can invoke when a change touches governed data. Same gate, same evidence, every time — across Snowflake, EMR/Iceberg, and application pipelines.

---

## Start here: 5-minute walkthrough video

Watch this first — it gives you the whole story end-to-end before you read a single line of code.

**▶ [Download the 5-minute walkthrough recording (96 MB MOV)](https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/releases/latest/download/abbvie-dataops-sdk-walkthrough.mov)**

Covers:
1. Architecture (5 lanes)
2. Repo structure and the manifest-first design
3. A live fail-closed PR governance gate (red → fix → green)
4. Automated merge → `schemachange` → SDK promote → immutable audit
5. End-to-end lineage in DataHub and Marquez

---

## Then: 10-minute self-guided tour

Once you've watched the video, you can verify everything yourself by opening these four tabs in order.

| # | What you'll see | Where |
|---|---|---|
| 1 | The whole story in one PR — broken commit (red gate), fix commit (green gate), automatic deploy after merge | **[Pull Request #2](https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/pull/2)** — *add WEBSITE column to ACCOUNTS* |
| 2 | The DDL change that triggered everything | [`migrations/snowflake/V1.3.0__add_website.sql`](migrations/snowflake/V1.3.0__add_website.sql) |
| 3 | The contract file the gate enforces | [`manifests/schemas/snowflake/accounts.json`](manifests/schemas/snowflake/accounts.json) |
| 4 | The manifest that wires it all together | [`manifests/snowflake-curated.yaml`](manifests/snowflake-curated.yaml) |

Then click into the **green check** on PR #2 → look at the `snowflake-deploy` log → see OIDC authentication, `schemachange` applying the migration, the SDK running governance in `promote` profile, and an evidence bundle uploaded as an artifact.

---

## What this PoC proves

| Claim | Evidence in this repo |
|---|---|
| **One SDK, three platforms** | `sdk/` Python package + three adapters: `snowflake`, `emr`, `suitecrm` |
| **One manifest format** | `manifests/*.yaml` — same shape regardless of platform |
| **No long-lived secrets** | GitHub Actions authenticates to both AWS and Snowflake via OIDC ([Snowflake CLI OIDC guide](https://www.snowflake.com/en/developers/guides/configure-cicd-integrations-with-snowflake/)) |
| **Fail-closed governance** | `pr-governance.yml` blocks any PR that touches governed data without an updated contract |
| **Lineage everywhere** | Every adapter emits OpenLineage events → Marquez captures runs → DataHub catalogs assets |
| **Immutable audit trail** | `SCHEMACHANGE.CHANGE_HISTORY` row with `INSTALLED_BY=GH_CICD_USER` for every applied change |
| **Reproducible** | `terraform/` for AWS + Snowflake account shells; `apps/datahub/bootstrap.sh` for catalog stand-up |

---

## Architecture

See **[`customer/POC_ARCHITECTURE.md`](customer/POC_ARCHITECTURE.md)** for three Mermaid diagrams:
1. End-to-end PoC architecture (5 lanes: source → CI/CD → SDK → governance backplane → data plane)
2. The data-change gate (PR governance decision tree)
3. End-to-end lineage chain (CRM → S3 → Iceberg → Snowflake → BI-safe view)

---

## Repo layout

| Path | What's in it |
|---|---|
| **`sdk/`** | The Python package (`abbvie-dataops-governance-sdk`) + `abbvie-dataops` CLI |
| **`manifests/`** | Per-service `dataops-manifest.yaml` files (the *entire* developer contract) |
| **`migrations/snowflake/`** | `schemachange` DDL scripts — the open-source standard for Snowflake DCM |
| **`pipelines/emr/`** | PySpark transform job + OpenLineage Spark listener config |
| **`apps/suitecrm/`** | SuiteCRM application (open-source CRM standing in for Salesforce in this PoC) |
| **`apps/datahub/`** | DataHub + Marquez deployment (Docker Compose + bootstrap) |
| **`.github/workflows/`** | Five CI/CD pipelines: `pr-governance`, `snowflake-deploy`, `emr-deploy`, `suitecrm-deploy`, `sdk-ci` |
| **`terraform/`** | Infrastructure-as-Code for AWS and Snowflake account shells |
| **`customer/POC_ARCHITECTURE.md`** | Architecture diagrams |

---

## How to run it in your own environment

The PoC is deployable into any AWS account + Snowflake account.

1. **Fill placeholders** in `terraform/aws/variables.tf` and `terraform/snowflake/main.tf` (account IDs, repo name, region).
2. **Provision AWS**: `cd terraform/aws && terraform init && terraform apply`
3. **Provision Snowflake**: run [`docs/SNOWFLAKE_BOOTSTRAP.sql`](docs/SNOWFLAKE_BOOTSTRAP.sql) once as `ACCOUNTADMIN`.
4. **Stand up DataHub + Marquez** on the EC2 host that Terraform allocates: `sudo bash /opt/abbvie/datahub/bootstrap.sh` (see [`apps/datahub/README.md`](apps/datahub/README.md)).
5. **Push to GitHub** with your repo name; the workflows then deploy themselves.

Full operator runbook: [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## The "data-change" rule in one sentence

> **If a PR adds, modifies, or removes governed data, it must update the corresponding contract in the same PR — otherwise the gate fails closed.**

Path-based detection (fast, free, runs on every PR). Profiles let you scope which checks run when:

- `develop` — PR-time, offline static validation
- `build` — CI staging environment
- `promote` — production-grade run on merge to `main`

---

## Open-source choices this PoC makes (and why)

| AbbVie target | PoC stand-in | Why it's a fair stand-in |
|---|---|---|
| Salesforce | **SuiteCRM** | Same role: application-of-record where business writes account data |
| Alation | **DataHub** | Same role: design-time catalog with owners, classification, search, glossary |
| Internal lineage store | **Marquez** | Reference OpenLineage backend; records every run (`START`/`COMPLETE`) for audit |
| Splunk / Datadog | Not in PoC scope | Production deployment would emit OpenTelemetry from the SDK to your existing observability stack |

The SDK does **not** replace JFrog, Terraform, Snyk, Great Expectations, or any tool AbbVie already owns — it standardizes *how* those capabilities are invoked and proven in CI/CD.

---

## Questions you'll probably have

**Is this Snowflake-only?**
No. Snowflake is one adapter. The same SDK runs against pure Glue/Iceberg/EMR with no Snowflake involvement.

**Does this work with Azure DevOps?**
Yes — the SDK is a Python package; the YAML around it is the only thing that differs between GitHub Actions and Azure DevOps.

**What about performance impact on PRs?**
The PR gate is path-based and runs only `develop` profile checks (schema + DQ smoke + manifest validation). Median added latency is under 90 seconds. Heavier `promote` checks only run on `main`.

**Who owns the SDK long-term?**
The data platform team, with per-platform adapters owned by the platform owners (Snowflake adapter ↔ Snowflake team, etc.).

**How do we extend this to AEM, Salesforce, et al.?**
Each new source is a new adapter (~150 lines of Python) + a manifest. The CI/CD wiring around it stays identical.

---


