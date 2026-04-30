# Acceptance demo — fail-closed on schema drift

This is the canonical demo for the PoC. It proves that the governance gate **blocks
a PR that produces a data change without updating the schema contract**, and that
the same gate **opens up** once the contract is fixed.

## Step 1 — Open the failing PR

```bash
git checkout -b feat/add-phone-broken
cat > migrations/snowflake/V1.2.0__add_phone.sql <<'SQL'
USE SCHEMA CURATED;
ALTER TABLE ACCOUNTS ADD COLUMN PHONE VARCHAR;
SQL
git add migrations/snowflake/V1.2.0__add_phone.sql
git commit -m "feat: add phone column (intentionally missing schema update)"
git push -u origin feat/add-phone-broken
gh pr create --base main --head feat/add-phone-broken \
  --title "feat: add phone column" --body "Demonstrates the fail-closed gate"
```

Expected: `pr-governance.yml` runs, comments the following on the PR, and exits non-zero.

```text
### DataOps governance gate
- is_data_change: true
- triggered_manifests: manifests/snowflake-curated.yaml
- must_fail_closed: true
- blockers:
  - changes under 'migrations/snowflake/' require an updated contract under 'manifests/schemas/snowflake/'
```

## Step 2 — Local repro (no GitHub needed)

```bash
echo "migrations/snowflake/V1.2.0__add_phone.sql" > /tmp/changed.txt
abbvie-dataops gate --changed-files /tmp/changed.txt --strict
echo "exit=$?"   # 2
```

## Step 3 — Fix the contract

```bash
# Add PHONE to the expected schema:
python - <<'PY'
import json, pathlib
p = pathlib.Path("manifests/schemas/snowflake/accounts.json")
doc = json.loads(p.read_text())
doc["columns"].append({"name": "PHONE", "data_type": "VARCHAR", "nullable": True})
p.write_text(json.dumps(doc, indent=2) + "\n")
PY
git add manifests/schemas/snowflake/accounts.json
git commit -m "fix: add phone to snowflake schema contract"
git push
```

Expected: `pr-governance.yml` re-runs, comment now shows `must_fail_closed: false`,
build is green, PR is mergeable.

## Step 4 — Merge and observe lineage

After merge, `snowflake-deploy.yml` runs schemachange + the SDK gate, and DataHub
shows the updated dataset with one upstream edge from
`urn:li:dataset:(urn:li:dataPlatform:glue,abbvie_dataops_poc_curated.accounts,PROD)`.
