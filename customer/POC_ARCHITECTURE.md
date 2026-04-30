# AbbVie DataOps SDK — PoC architecture (AWS build)

Three Mermaid diagrams to drop into Confluence / Word. The PoC swaps Salesforce
for **SuiteCRM** (open-source CRM, Salesforce analog) and Alation for **DataHub**;
everything else mirrors the customer architecture in `ABBVIE_DATAOPS_SDK_WRITEUP_AND_TALK_TRACK.md`.

## Diagram 1 — End-to-end PoC architecture

```mermaid
flowchart LR
  subgraph REQ[Requirements and Change]
    JIRA[Jira / ServiceNow]
    DEV[Developer]
  end

  subgraph SRC[Source Control]
    REPO[GitHub repo<br/>app or data pipeline]
    MANIFEST[dataops-manifest.yaml]
  end

  subgraph CI[CI / CD]
    GHA[GitHub Actions<br/>5 workflows]
  end

  subgraph SDK[AbbVie DataOps Governance SDK]
    CORE[Core + CLI]
    MOD1[Schema enforcement]
    MOD2[Data quality]
    MOD3[Constraints]
    MOD4[Tokenization]
    MOD5[Lineage emit]
    MOD6[Catalog emit]
  end

  subgraph ADAPT[Platform adapters]
    A_SF[Snowflake adapter]
    A_EMR[EMR / Glue / Iceberg adapter]
    A_APP[SuiteCRM adapter]
  end

  subgraph ENT[Enterprise services]
    DATAHUB["DataHub<br/>(EC2 i-0165db8e63bcdb1d3)"]
    MARQUEZ["Marquez<br/>(co-located on same EC2)"]
    OL[OpenLineage spec]
    OIDC[AWS + Snowflake OIDC]
    SECRETS[AWS Secrets Manager]
    TF[Terraform IaC]
    S3[(S3 + Glue + Iceberg)]
    EMR[EMR Serverless]
    ECS[ECS Fargate + RDS]
    SF[(Snowflake)]
  end

  DEV --> JIRA
  DEV --> REPO
  REPO --> MANIFEST
  REPO --> GHA

  GHA -->|invoke| CORE
  MANIFEST -->|config| CORE
  CORE --> MOD1 & MOD2 & MOD3 & MOD4 & MOD5 & MOD6

  MOD1 --> A_SF & A_EMR & A_APP
  MOD2 --> A_SF & A_EMR & A_APP
  MOD3 --> A_SF & A_APP
  MOD4 --> A_SF & A_APP
  MOD5 -->|HTTP| MARQUEZ
  MOD6 -->|REST| DATAHUB

  A_SF --> SF
  A_EMR --> EMR --> S3
  A_APP --> ECS --> S3

  MARQUEZ --> DATAHUB
  OL -.spec.-> MOD5
  OIDC -.auth.-> GHA
  SECRETS -.secrets.-> GHA
  TF -.provisions.-> S3 & EMR & ECS & SF
```

## Diagram 2 — The data-change gate (PR governance)

```mermaid
flowchart TD
  START[Pull request to main] --> DETECT["abbvie-dataops gate<br/>(path-based change detector)"]
  DETECT -->|touches governed data| REQD[manifests selected]
  DETECT -->|app-only change| SKIP[no SDK run required]

  REQD --> CHECK["For each triggered manifest<br/>run develop profile"]
  CHECK --> EVIDENCE[Upload evidence bundle + PR comment]
  EVIDENCE --> CONTRACT[Required contract files updated?]
  CONTRACT -->|yes| GREEN[PR can merge]
  CONTRACT -->|no| BLOCK[Fail closed]

  SKIP --> GREEN
```

## Diagram 3 — End-to-end lineage chain

```mermaid
sequenceDiagram
  autonumber
  participant Dev as Developer
  participant CI as GitHub Actions
  participant SDK as DataOps SDK
  participant CRM as SuiteCRM (ECS + RDS)
  participant Spark as EMR Serverless
  participant Iceberg as S3 + Glue + Iceberg
  participant SF as Snowflake
  participant Marquez as Marquez (EC2)
  participant DH as DataHub (EC2)

  Dev->>CI: Merge to main
  CI->>CRM: docker build + push, RDS migrations, run extractor
  CRM->>Iceberg: write s3://raw/suitecrm/accounts/*.parquet
  CRM->>Marquez: COMPLETE event for suitecrm.public.accounts
  CI->>SDK: abbvie-dataops run (suitecrm manifest)
  SDK->>DH: register dataset + owners + tags

  CI->>Spark: start-job-run transform_accounts
  Spark->>Iceberg: write glue_catalog.curated.accounts
  Spark->>Marquez: START + COMPLETE events (OL Spark listener)
  CI->>SDK: abbvie-dataops run (emr manifest)
  SDK->>DH: register glue dataset with upstream urn -> mysql.suitecrm.accounts

  CI->>SF: schemachange apply
  CI->>SDK: abbvie-dataops run (snowflake manifest)
  SDK->>DH: register snowflake dataset with upstream urn -> glue.curated.accounts
  SDK->>Marquez: COMPLETE event
  DH-->>Dev: end-to-end lineage suitecrm -> glue -> snowflake
```
