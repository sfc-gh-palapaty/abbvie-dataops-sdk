# VP Demo — Quick Reference Card

> One-page cheat sheet. For the full talk track + Q&A, open `VP_DEMO_RUNBOOK.md`.

---

## Endpoints + creds

| Service | URL | Login |
|---|---|---|
| DataHub UI | http://34.205.77.61:9002 | `datahub` / `datahub` |
| Marquez UI | http://34.205.77.61:13000 | (no auth) |
| OpenLineage API | http://34.205.77.61:5000 | (no auth) |
| GitHub repo | https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk | (your PAT) |
| GitHub Actions | https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/actions | |
| EC2 (DataHub + Marquez) | `i-0165db8e63bcdb1d3` (us-east-1) | SSM |
| AWS account | `194722405805` | SSO |
| Snowflake account | `SFSENORTHAMERICA-PHANI_AWS1` (locator `FZB62295`) | OIDC from GHA |

---

## Pre-flight (run 30 min before the meeting)

```bash
# Fresh AWS creds, then:
cd ~/Documents/Abbvie/abbvie-dataops-poc-aws
git pull

# Re-seed lineage so Marquez timelines look fresh
OPENLINEAGE_URL=http://34.205.77.61:5000 \
DATAHUB_GMS_URL=http://34.205.77.61:8000 \
python customer/seed_demo_lineage.py

# Quick health pings
curl -fsS http://34.205.77.61:9002/api/health  >/dev/null && echo "DataHub OK"
curl -fsS http://34.205.77.61:13000            >/dev/null && echo "Marquez OK"
curl -fsS http://34.205.77.61:5000/api/v1/namespaces | head -c 80
```

---

## 7 tabs to pre-open (in order)

| # | What | URL |
|---|---|---|
| **T1** | Repo `main` | https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk |
| **T2** | Actions list | https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/actions |
| **T3** | The merged schema-drift PR (#1) | https://github.com/sfc-gh-palapaty/abbvie-dataops-sdk/pull/1 |
| **T4** | DataHub — SuiteCRM (mysql) source | http://34.205.77.61:9002/dataset/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Amysql%2Csuitecrm.public.accounts%2CPROD%29 |
| **T5** | DataHub — Snowflake governance view | http://34.205.77.61:9002/dataset/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Asnowflake%2Cabbvie_dataops_dev.curated.v_accounts_governed%2CPROD%29 |
| **T6** | Marquez UI | http://34.205.77.61:13000 |
| **T7** | `customer/POC_ARCHITECTURE.md` | local IDE |

> **Pro-tip:** on T4, click `Lineage` tab and pre-expand the graph 4 times so all 5 nodes are already visible when you switch tabs in front of the VP.

---

## 7 demo beats (1–2 min each)

| Beat | Tab | What you say + click |
|---|---|---|
| **A** Developer push | T1 | Show `migrations/snowflake/V1.2.0__add_phone.sql` + `manifests/snowflake-curated.yaml`. *"This is the entire developer contract."* |
| **B** PR fails closed | T3 | Red `pr-governance` check + bot comment with `must_fail_closed: true`. *"Path-based gate. Fast. Free."* |
| **C** Contract fix | T3 | Show the follow-up commit adding `PHONE` to `manifests/schemas/snowflake/accounts.json`. Check goes green. |
| **D** Merge → deploy | T2 | `snowflake-deploy` log: OIDC → schemachange → SDK promote → evidence bundle. |
| **E** End-to-end lineage | T4 | Click `+` four times: `mysql → s3 → glue → snowflake → snowflake_view`. End on `v_accounts_governed` schema (`EMAIL_TOKENIZED`, `PHONE_TOKENIZED`, `ANNUAL_REVENUE_BUCKETED`). |
| **F** Run history | T6 | Switch namespaces `abbvie.suitecrm / s3 / glue / snowflake`. *"DataHub = what exists. Marquez = what ran."* |
| **G** Reproducibility | IDE | Wave at `terraform/`, `apps/datahub/bootstrap.sh`, `docs/SNOWFLAKE_BOOTSTRAP.sql`. *"No special snowflake."* |

---

## Lineage chain (memorize)

```
SuiteCRM (mysql)
  └─ suitecrm.public.accounts
        ↓  suitecrm.accounts.land_to_s3
S3 raw zone
  └─ abbvie-dataops-poc-raw-194722405805/suitecrm/accounts
        ↓  emr.curated.accounts.transform   (EMR Serverless / PySpark)
Glue + Iceberg curated
  └─ abbvie_dataops_poc_curated.accounts
        ↓  snowflake.curated.accounts.upsert  (schemachange + SDK)
Snowflake curated
  └─ abbvie_dataops_dev.curated.accounts
        ↓  snowflake.curated.v_accounts_governed.refresh
Snowflake governance view (BI-safe)
  └─ abbvie_dataops_dev.curated.v_accounts_governed
       (EMAIL_TOKENIZED, PHONE_TOKENIZED, ANNUAL_REVENUE_BUCKETED)
```

---

## Three sentences if the meeting gets cut to 5 min

1. *"One small SDK plus a YAML manifest gives every AbbVie pipeline — GitHub Actions, Azure DevOps, Glue, EMR, Snowflake, app pipelines — the same governance gate."*
2. *"PRs that touch governed data without an updated contract fail closed; PRs that don't, sail through. Lineage and catalog are populated automatically on every merge."*
3. *"The PoC proves it across SuiteCRM → S3 → EMR/Iceberg → Snowflake. Snowflake is one adapter, not the assumption."*

---

## Top 3 anticipated questions

| Q | A |
|---|---|
| Snowflake-only? | No. Snowflake is one adapter; same SDK runs against pure Glue/Iceberg/EMR. |
| Why DataHub *and* Marquez? | DataHub = design-time catalog (what exists, who owns). Marquez = runtime lineage (what ran, when, did it succeed). Marquez ingests into DataHub → one pane. |
| PR latency? | Path-based + develop profile only on PRs. Median added latency < 90s. Promote profile (heavier) only runs on merge to `main`. |
