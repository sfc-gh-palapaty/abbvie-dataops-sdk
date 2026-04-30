# AWS infrastructure for the AbbVie DataOps PoC

Provisions the AWS-side of the PoC in account `194722405805` (us-west-2 by default):

- 4 S3 buckets: `raw`, `curated`, `lineage`, `artifacts`
- 2 Glue databases: `..._bronze`, `..._curated` (Iceberg)
- EMR Serverless Spark application + runtime IAM role
- ECR repo + ECS Fargate cluster + RDS MySQL for SuiteCRM
- IAM OIDC provider + role assumed by GitHub Actions (`sfc-gh-palapaty/abbvie-dataops-poc-aws`)
- Secrets Manager entries for SuiteCRM DB, DataHub endpoints, Snowflake connection
- Security group rules opening DataHub ports `8080/8000/5000` on EC2 `i-0165db8e63bcdb1d3` to PoC workloads

## Bring-up

```bash
export AWS_REGION=us-west-2
terraform init
terraform plan -out tf.plan
terraform apply tf.plan
```

The DataHub EC2 instance (`i-0165db8e63bcdb1d3`) must already exist; this stack only adds ingress rules to its security group.

## Outputs to copy into GitHub repo settings

After `apply`, set these as GitHub Actions **repository variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Source |
|---|---|
| `AWS_GHA_ROLE_ARN` | output `github_actions_role_arn` |
| `AWS_REGION` | `us-west-2` |
| `EMR_APPLICATION_ID` | output `emr_serverless_application_id` |
| `EMR_RUNTIME_ROLE_ARN` | output `emr_runtime_role_arn` |
| `S3_RAW_BUCKET` / `S3_CURATED_BUCKET` / `S3_LINEAGE_BUCKET` / `S3_ARTIFACTS_BUCKET` | output `s3_buckets` |
| `GLUE_BRONZE_DB` / `GLUE_CURATED_DB` | output `glue_databases` |
| `ECR_REPOSITORY_URL` | output `ecr_repository_url` |
| `ECS_CLUSTER_NAME` | output `ecs_cluster_name` |
| `DATAHUB_ENDPOINTS_SECRET_ARN` | output `datahub_endpoints_secret_arn` |

Snowflake auth is OIDC (no AWS secret); only `SNOWFLAKE_ACCOUNT` is needed as a separate GitHub variable.
