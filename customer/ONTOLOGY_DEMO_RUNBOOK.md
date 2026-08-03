# Ontology Demo Runbook — Business Documents → OSI YAML

**Use case:** AbbVie reads business documents from SharePoint (demo: S3 or local files), parses them into a governed ontology layer, and emits **Open Semantic Interchange (OSI)** YAML versioned in git. The YAML can be imported into Snowflake semantic views, AWS Glue semantic layers, or any OSI-compliant platform.

---

## Architecture

```
SharePoint (prod)          S3 landing zone (demo)
       │                          │
       └──────────┬───────────────┘
                  ▼
         Data Ops SDK Ontology Pipeline
    (parse ERD + business rules + source-to-target)
                  │
                  ▼
         OSI YAML (git outputs/ontology/)
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
 Snowflake              AWS / other
 SYSTEM$CREATE_         OSI converters
 SEMANTIC_VIEW_         (Glue, dbt, etc.)
 FROM_OSSIE_YAML
```

This use case integrates with the existing Data Ops SDK demo as a **sixth lane**: unstructured business knowledge → governed semantic model, alongside the structured CRM → S3 → EMR → Snowflake pipeline.

---

## Input documents

| Document | Simulates | Location |
|----------|-----------|----------|
| `pharma_erd.md` | PowerPoint / Confluence ERD | `data/ontology/` |
| `business_rules.md` | Business rules deck v2.1 | `data/ontology/` |
| `source_to_target.csv` | Data mapping spreadsheet | `data/ontology/` |

In production, SharePoint documents land in an S3 prefix via Azure Data Factory or similar. Set `s3_bucket` and `s3_prefix` in the manifest.

---

## Quick start (local demo)

```bash
cd abbvie-dataops-poc-aws/sdk
pip install -e ".[all]"

# Build OSI YAML directly
abbvie-dataops ontology \
  --repo-root .. \
  --output-dir ../outputs/ontology

# Or via manifest (full SDK path with lineage emission)
abbvie-dataops run \
  --manifest ../manifests/pharma-ontology.yaml \
  --repo-root .. \
  --profile promote \
  --evidence-out ../evidence-ontology.json
```

**Outputs:**
- `outputs/ontology/abbvie_pharma_intelligence_v2.1.0.yaml` — OSI 0.1.1 semantic model
- `outputs/ontology/manifest.json` — version metadata, content hash, materialization hints

---

## S3 demo (SharePoint stand-in)

Upload the three documents to your raw bucket:

```bash
aws s3 cp data/ontology/ s3://YOUR_RAW_BUCKET/ontology/ --recursive
```

Then run:

```bash
abbvie-dataops ontology \
  --s3-bucket YOUR_RAW_BUCKET \
  --s3-prefix ontology \
  --repo-root . \
  --output-dir outputs/ontology
```

---

## Import into Snowflake semantic view

After the YAML is in git (or staged in Snowflake):

```sql
-- Read the OSI YAML file (upload to @stage or paste content)
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML(
  'ABBVIE_DATAOPS_DEV.CURATED',
  $$
  -- paste contents of abbvie_pharma_intelligence_v2.1.0.yaml here
  $$
);

-- Verify round-trip
SELECT SYSTEM$READ_OSSIE_YAML_FROM_SEMANTIC_VIEW('ABBVIE_DATAOPS_DEV.CURATED.ABBVIE_PHARMA_INTELLIGENCE');
```

The generated model includes:
- **8 datasets** (patients, drugs, prescribers, facilities, prescriptions, therapy_areas, treatment_pathways, adverse_events)
- **Relationships** from the ERD (IS_PRESCRIBED, PRESCRIBES, TREATS, etc.)
- **Metrics** derived from business rules (switch rate, KOL count, prescription totals)
- **Custom extensions** with abstract classes, inference rules, and hierarchy (ABBVIE vendor block)

---

## Integration with Data Ops SDK demo

| SDK component | Ontology use case |
|---------------|-------------------|
| Manifest | `manifests/pharma-ontology.yaml` |
| Adapter | `ontology` — reads docs, builds OSI YAML |
| PR gate | Changes under `data/ontology/` trigger `pharma-ontology.yaml` |
| Lineage | OpenLineage: S3 docs → git OSI YAML; DataHub: git dataset node |
| Evidence | `evidence-ontology.json` artifact in CI |
| Horizon / Cortex | OSI YAML → Snowflake semantic view → Cortex Analyst grounding |

### Demo talk track (3 min add-on)

1. **Problem:** Business rules live in SharePoint decks; data teams re-implement logic in every pipeline.
2. **Show:** `data/ontology/business_rules.md` — treatment switching rules, KOL criteria.
3. **Run:** `abbvie-dataops ontology --repo-root ..`
4. **Show:** Generated YAML in `outputs/ontology/` — datasets, metrics, ABBVIE custom extensions.
5. **Import:** Snowflake `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML` (or show pre-created view).
6. **Close:** Same YAML works on AWS via OSI hub-and-spoke converters — one source of truth.

---

## Version control

Every ontology build writes:
- Versioned YAML: `{model_name}_v{version}.yaml`
- Manifest with SHA-256 content hash for drift detection

When business documents change in SharePoint:
1. Updated docs land in S3 (or are committed to `data/ontology/`)
2. CI triggers `ontology-deploy.yml` workflow
3. New OSI YAML committed to `outputs/ontology/` automatically
4. Snowflake semantic view refreshed via DCM / deploy workflow

### GitHub Actions workflow

The `ontology-deploy.yml` workflow runs on push to `main` when:
- `data/ontology/**` changes
- `manifests/pharma-ontology.yaml` changes
- SDK ontology module changes

It builds the OSI model, validates output, uploads evidence artifacts, and auto-commits regenerated YAML to `outputs/ontology/`.

Manual trigger with S3 sources (SharePoint stand-in):
```bash
gh workflow run ontology-deploy.yml \
  -f s3_bucket=abbvie-dataops-poc-raw \
  -f s3_prefix=ontology
```

---

## Architecture diagram

See **`DataOps SDK flow.excalidraw`** (Lane 6) in the AbbVie workspace root for the visual flow:
SharePoint/S3 → Ontology Pipeline → OSI YAML (git) → Snowflake Semantic View / AWS

---

## Files

| Path | Purpose |
|------|---------|
| `data/ontology/` | Input business documents |
| `outputs/ontology/` | Versioned OSI YAML outputs (committed) |
| `manifests/pharma-ontology.yaml` | SDK manifest |
| `sdk/src/abbvie_dataops_governance/ontology/` | Parser + OSI builder |
| `migrations/snowflake/R__pharma_semantic_view.sql` | Optional Snowflake import helper |
