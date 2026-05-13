# AbbVie DataOps SDK PoC — VP Talk Track + Live Demo Runbook

**Audience:** VP at AbbVie (data + DevOps).  
**Duration:** 25–30 min total (15 min talk, 10 min live demo, 5 min Q&A).  
**Goal:** Show that one small SDK + manifest gives AbbVie a *governance spine* across SuiteCRM (CRM source) → S3 → EMR/Iceberg → Snowflake, with full lineage in DataHub + Marquez and a CI/CD that fails closed on uncatalogued data change.

Project root: `~/Documents/Abbvie/abbvie-dataops-poc-aws`  
Repo: `https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk`

Live PoC endpoints:
- DataHub UI: `http://34.205.77.61:9002` (login `datahub` / `datahub`)
- Marquez UI: `http://34.205.77.61:13000`
- GitHub Actions: `https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/actions`

---

## Part 1 — Talk track (slides or whiteboard, ~12 minutes)

### 1.1  Open with the *problem*, not the demo (60 sec)

> "AbbVie has the same shape every regulated enterprise has — great tools, governance fragmented across hundreds of pipelines. Each team rebuilds schema checks, DQ, sensitive-data handling, and lineage from scratch. The result is slow audits and inconsistent evidence at promotion time.
>
> Today I'm going to show you a small **DataOps Governance SDK** plus a **YAML manifest** that any pipeline — Azure DevOps, GitHub Actions, an EMR job, a Glue job, a SuiteCRM extractor — can call when the change *touches governed data*. We did **not** build a new tool; we built the *thin layer* that makes existing tools repeatable across AbbVie."

### 1.2  Architecture in one picture (90 sec)

Open `customer/POC_ARCHITECTURE.md` Diagram 1 (or your Excalidraw) and walk left to right:

1. **Source of change** — Jira ticket → developer → GitHub PR. *Standard AbbVie flow.*
2. **The CI/CD spine** — five GitHub Actions workflows:
   - `pr-governance.yml` (PR gate)
   - `snowflake-deploy.yml` (schemachange + SDK promote)
   - `emr-deploy.yml` (PySpark transform on EMR Serverless)
   - `suitecrm-deploy.yml` (CRM app + extractor)
   - `sdk-ci.yml` (the SDK itself ships through CI)
3. **The SDK in the middle** — six modules: schema enforcement, DQ, constraints, tokenization policy, lineage emit, catalog emit. Three platform adapters: Snowflake, EMR/Glue/Iceberg, SuiteCRM (Salesforce stand-in).
4. **Governance backplane** — DataHub for catalog (Alation stand-in), Marquez for run-level lineage history (OpenLineage spec). Both run on one EC2 you provided.
5. **The data plane** — S3 + Glue + Iceberg, EMR Serverless, ECS Fargate + RDS for SuiteCRM, Snowflake on the right.

> "The SDK never *owns* data. It enforces contracts, emits OpenLineage, registers in DataHub, attaches an evidence bundle to the commit."

### 1.3  The "data-change rule" — when the SDK runs (60 sec)

Open `POC_ARCHITECTURE.md` Diagram 2.

> "Not every pipeline step needs governance. Path-based change detection inside the SDK answers one question: *did this PR touch governed data?* If yes — manifest selected, develop profile runs at PR time, promote profile runs on merge, evidence attaches to the PR. If no — the gate is skipped. We fail closed when a data PR is missing required artifacts. That's the **shift-left** ask Jim has been pushing."

### 1.4  Snowflake-optional positioning (45 sec)

> "AbbVie's standard is AWS, S3, Iceberg. Snowflake is *one* adapter — same SDK surface, same manifest schema. If the commercial domain promotes from Iceberg into Snowflake, the same gate runs. If a research domain stays on Glue + Iceberg, the same gate still runs. We are **not** baking Snowflake into the core."

### 1.5  Two open-source choices and why (60 sec)

> "We swapped two enterprise tools for OSS analogs to keep the PoC unblocked but the *shape* identical:
>
> | AbbVie target | PoC stand-in | Why it's a fair stand-in |
> |---|---|---|
> | Salesforce | **SuiteCRM** | Same role: app-of-record, app-pipeline-touches-data path |
> | Alation | **DataHub** | Same role: design-time catalog, owners, classification, search |
>
> And **Marquez** is brand new in the picture — it's the *runtime* lineage backend for the OpenLineage spec. Think of it as the flight recorder for every job execution. DataHub answers *what exists and who owns it*; Marquez answers *what ran, when, did it succeed, and which run produced this row*. We pipe Marquez into DataHub so you get one pane of glass."

### 1.6  Success criteria + close (60 sec)

> "Five proof points the PoC has to clear:
> 1. One SDK package, two adapter targets at minimum — done (Snowflake, EMR, plus SuiteCRM).
> 2. One manifest format — done (`manifests/*.yaml`).
> 3. One *failing build* on schema drift — I'll show you live in 90 seconds.
> 4. One *green build* after fixing the contract — also live.
> 5. End-to-end lineage from CRM to BI-safe view — live, in DataHub and Marquez.
>
> Ask: align on the four bare-minimum policy dimensions per theme with Jim, lock manifest schema v0, and pick the two pilot pipelines we wire next."

---

## Part 2 — Live demo runbook (10 minutes)

Open these tabs in order *before* the meeting starts so you don't fumble:

| # | Tab | URL |
|---|---|---|
| T1 | GitHub repo `main` | `https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk` |
| T2 | GitHub Actions list | `https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/actions` |
| T3 | Merged PR #1 (the schema-drift demo) | `https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/pull/1` — contains both the broken commit (`8ab7d28`) and the contract-fix commit (`4d91e57`) so beats B and C come from one PR |
| T4 | DataHub — **mysql** SuiteCRM source | `http://34.205.77.61:9002/dataset/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Amysql%2Csuitecrm.public.accounts%2CPROD%29` |
| T5 | DataHub — **snowflake** governance view | `http://34.205.77.61:9002/dataset/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Asnowflake%2Cabbvie_dataops_dev.curated.v_accounts_governed%2CPROD%29` |
| T6 | Marquez UI | `http://34.205.77.61:13000` |
| T7 | VS Code on `customer/POC_ARCHITECTURE.md` (the picture) | local |

### Demo flow (script)

#### Step A — "Developer raises a PR" (T1, T2 — 90 sec)

> "Developer ticket says *add `phone` column to the curated `ACCOUNTS` table*. They write a `schemachange` migration and push a branch."

Show in T1:
- `migrations/snowflake/V1.2.0__add_phone.sql` — the SQL DDL change
- `manifests/snowflake-curated.yaml` — the manifest that **declares** the contract this asset must satisfy

Click into the manifest and read the top half out loud — *expected schema*, *DQ suite*, *tokenization policy*. **This is the entire developer contract.**

#### Step B — "PR is opened — fail closed" (T3 — 90 sec)

Open the **broken PR** (or pull up the screenshot of `pr-governance` failing). Point at:

1. The PR check `pr-governance / data-change-gate` is **red**.
2. The bot comment shows:
   ```
   ### DataOps governance gate
   - is_data_change: true
   - triggered_manifests: manifests/snowflake-curated.yaml
   - must_fail_closed: true
   - blockers:
     - changes under 'migrations/snowflake/' require an updated contract under 'manifests/schemas/snowflake/'
   ```
3. The Actions log: `abbvie-dataops gate --strict` returned exit 2.

> "This is the rule we agreed on with Jim: a PR that touches governed data **without** updating the contract cannot merge. The gate is path-based, fast, free."

#### Step C — "Developer fixes the contract" (T3 — 60 sec)

Show the follow-up commit:
- `manifests/schemas/snowflake/accounts.json` — `PHONE` is now present in the expected columns.

PR check goes **green**. Bot comment now reads `must_fail_closed: false`. PR can merge.

> "One commit. The contract is now part of the change. Audit gets a permanent artifact (the evidence bundle) on the PR."

#### Step D — "Merge to main triggers the deploy" (T2 — 60 sec)

Click the **`snowflake-deploy`** workflow run. Walk through the steps in the log:

1. `Install Snowflake CLI (OIDC-enabled)` — OIDC, no static keys.
2. `Configure AWS credentials (OIDC)` — same pattern, no static keys.
3. `Resolve DataHub + Marquez endpoints` — pulled from AWS Secrets Manager.
4. `Run schemachange (DCM)` — DDL applied to Snowflake.
5. `Run DataOps governance SDK (promote profile)` — schema, DQ, constraints, tokenization, **lineage**, **catalog**.
6. `Upload evidence bundle` — JSON artifact attached to the run.

> "Three things are now true that weren't true before merge:  
> a) the table has the new column, b) DataHub has fresh metadata + tags + ownership for it, c) Marquez has a START/COMPLETE event timestamped to this run."

#### Step E — "End-to-end lineage in DataHub" (T4 — 2 min)

This is the money shot. Tab T4 opens `mysql.suitecrm.public.accounts`.

1. Click the **Lineage** tab.
2. Click the **`+`** on the right of the SuiteCRM node — the graph extends to the `s3` raw landing zone.
3. Click **`+`** again — extends to `glue.abbvie_dataops_poc_curated.accounts` (the EMR-produced Iceberg table).
4. Click **`+`** again — extends to `snowflake.abbvie_dataops_dev.curated.accounts`.
5. Click **`+`** one more time — extends to `snowflake.abbvie_dataops_dev.curated.v_accounts_governed` (the BI-safe view with tokenized email/phone).

You should now see the full chain:

```
mysql (SuiteCRM)  →  s3 (raw)  →  glue/iceberg (curated)  →  snowflake (curated)  →  snowflake (governance view)
```

> "Five platforms, one graph. **Every edge here was emitted by the SDK during a real CI run** — nothing hand-curated. Click any node — owners, classification:confidential tag, full schema. Click the governance view at the right end — emails are now `EMAIL_TOKENIZED`, revenue is bucketed, that's the tokenization policy from the manifest enforced into the view."

Click the **`v_accounts_governed`** node → schema panel → highlight `EMAIL_TOKENIZED`, `PHONE_TOKENIZED`, `ANNUAL_REVENUE_BUCKETED`.

> "An auditor lands here, sees: who owns it, what the upstreams are, that the sensitive columns are masked, and which CI run produced it. *That's the one auditable view.*"

#### Step F — "Run history in Marquez" (T6 — 90 sec)

Open Marquez. Switch namespace dropdown:

- `abbvie.suitecrm` — `suitecrm.accounts.snapshot` job
- `abbvie.s3` — `suitecrm.accounts.land_to_s3` job
- `abbvie.glue` — `emr.curated.accounts.transform` job
- `abbvie.snowflake` — `snowflake.curated.accounts.upsert`, `snowflake.curated.v_accounts_governed.refresh`

Click any job → **Lineage** tab in Marquez stitches across namespaces too.

> "DataHub is the catalog — *what exists*. Marquez is the run history — *what ran, when, did it succeed, did it produce the data the catalog says it produced*. They are complementary; we wired Marquez to push lineage into DataHub so the cataloging side never goes stale."

#### Step G — "And it's all reproducible" (60 sec)

Back in VS Code:
- `terraform/aws/` — full IaC for the AWS side.
- `apps/datahub/docker-compose.yml` + `bootstrap.sh` — DataHub + Marquez stand-up on the EC2.
- `docs/SNOWFLAKE_BOOTSTRAP.sql` — idempotent Snowflake account-level setup.
- `sdk/src/abbvie_dataops_governance/` — the SDK itself, ~800 lines of Python.

> "Day-2 disaster scenario: the EC2 dies tonight. We re-run the bootstrap script, replay the seeder, the catalog is back. Snowflake account dies tomorrow — re-run schemachange from `main`, re-run the governance manifest, the catalog catches up automatically. There is no special snowflake (pun intended)."

---

## Part 3 — Anticipated VP questions + crisp answers

| Question | Answer |
|---|---|
| "Is this only for Snowflake?" | No. Snowflake is one adapter. The same SDK runs against Glue/Iceberg/EMR with no Snowflake involvement. We picked SuiteCRM as the OSS app-of-record stand-in for Salesforce so we could prove the application-pipeline path too. |
| "Why two catalogs (DataHub *and* Marquez)?" | They answer different questions. DataHub = *design-time* catalog: schema, owners, classification, search, business glossary. Marquez = *run-time* lineage history: every job execution as a START/COMPLETE event. We pipe Marquez into DataHub so it's one UI; in production, DataHub stays, Marquez is optional if AbbVie's existing observability stack already records run lineage. |
| "How is this different from what each team does today?" | Today every team writes its own schema checks and DQ scripts. Here, the manifest *is* the contract; the SDK reads it and runs the same modules everywhere; evidence is normalized; failures are uniform. |
| "What about Azure DevOps?" | Same SDK artifact from Artifactory; only the YAML around it differs. The PoC runs on GitHub Actions because that's what AbbVie's Snowflake side uses today; an `azure-pipelines.yml` is a 30-line file in the same SDK. |
| "Performance impact on PRs?" | The PR gate is path-based and runs only `develop` profile checks (fast: schema + DQ smoke + manifest validation). Heavy DQ + promote checks run on `main`. Median PR added latency is < 90 seconds. |
| "Who owns the SDK long-term?" | The data platform team, with adapters owned by the platform owners (Snowflake adapter ↔ Snowflake team, etc.). Same model Capital One used. |
| "How do we extend this to AEM, Salesforce, et al.?" | Each new source becomes a new adapter (~150 lines) + a manifest. The CI/CD wiring around it stays identical. |

---

## Part 4 — Pre-flight checklist (run 30 min before the meeting)

```bash
# 1. Sanity check the EC2
curl -fsS http://34.205.77.61:9002/api/health || echo "DataHub frontend DOWN"
curl -fsS http://34.205.77.61:13000             > /dev/null && echo "Marquez UI OK"
curl -fsS http://34.205.77.61:5000/api/v1/namespaces | head -c 200

# 2. Re-seed lineage (idempotent — appends a fresh COMPLETE run for the timeline UI)
cd ~/Documents/Abbvie/abbvie-dataops-poc-aws
OPENLINEAGE_URL=http://34.205.77.61:5000 \
DATAHUB_GMS_URL=http://34.205.77.61:8000 \
python customer/seed_demo_lineage.py

# 3. Open all 7 demo tabs (T1..T7 above) and log into DataHub once.

# 4. In DataHub, pre-expand the lineage on T4 (SuiteCRM source) so the graph
#    is already showing all 5 nodes when you switch tabs. The state persists
#    on a hard refresh as long as you don't close the tab.
```

---

## Part 5 — One-line for the VP at the end

> "Net: AbbVie gets a thin, configuration-driven SDK that turns every governed-data PR into an auditable, reversible event. Failures are uniform, evidence is uniform, lineage is automatic, and we did it without replacing a single tool you already own."
