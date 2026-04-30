# PoC runbook

Step-by-step operating instructions for the AbbVie DataOps PoC.

## 1. AWS account bring-up

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=...           # account 194722405805
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

cd terraform/aws
terraform init
terraform plan -out tf.plan
terraform apply tf.plan
terraform output -json > ../../docs/_outputs.json
```

The `outputs.tf` block lists every value you need to copy into GitHub repository
**Variables** (Settings -> Secrets and variables -> Actions -> Variables).

## 2. DataHub + Marquez on the EC2

```bash
# from your laptop, replace <pubip> with the EC2 public address
ssh ubuntu@<pubip> 'mkdir -p /tmp/abbvie && exit'
scp apps/datahub/{docker-compose.yml,bootstrap.sh} ubuntu@<pubip>:/tmp/abbvie/
ssh ubuntu@<pubip> 'sudo bash /tmp/abbvie/bootstrap.sh'
```

Verify ports `8080`, `8000`, `5000` are reachable from your VPC. The bootstrap
script will write the resolved private IP into the
`abbvie-dataops-poc/datahub/endpoints` Secrets Manager entry.

## 3. Snowflake bring-up (manual SQL + Terraform)

Run the SQL in `docs/SNOWFLAKE_OIDC_SETUP.sql` (creates the OIDC service user).
Then `terraform -chdir=terraform/snowflake apply`.

Set GitHub repo Variables:

- `SNOWFLAKE_ACCOUNT` -> e.g. `xy12345.us-east-1.aws`
- `SNOWFLAKE_USER` -> `GH_CICD_USER`
- `SNOWFLAKE_ROLE` -> `ABBVIE_DATAOPS_DEPLOY`
- `SNOWFLAKE_WAREHOUSE` -> `ABBVIE_DATAOPS_WH`
- `SNOWFLAKE_DATABASE` -> `ABBVIE_DATAOPS_DEV`

## 4. Push code to GitHub

```bash
gh repo create sfc-gh-palapaty/abbvie-dataops-poc-aws --public --source=. --push
```

## 5. Acceptance demo (the failure path)

1. Branch `feat/add-phone` from `main`.
2. Add `migrations/snowflake/V1.2.0__add_phone.sql` with `ALTER TABLE ACCOUNTS ADD COLUMN PHONE VARCHAR;`.
3. **Do not** edit `manifests/schemas/snowflake/accounts.json`.
4. Open PR -> `pr-governance.yml` posts a comment listing the blocker and fails.
5. Add `phone` to the schema JSON in a new commit -> gate goes green -> merge.
6. `snowflake-deploy.yml` runs schemachange + SDK gate -> dataset re-registered in DataHub.
7. Inspect lineage in DataHub UI: **suitecrm.public.accounts -> glue.curated.accounts -> snowflake.curated.accounts**.
