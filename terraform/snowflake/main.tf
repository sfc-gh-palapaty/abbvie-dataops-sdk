# Snowflake account-level shell for the PoC.
# Tables and views are managed by schemachange under migrations/snowflake.
# Reference: https://www.snowflake.com/en/developers/guides/devops-dcm-schemachange-github/

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.95"
    }
  }
}

provider "snowflake" {
  # Configure via SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_AUTHENTICATOR=oauth/jwt env vars.
  role = "ACCOUNTADMIN"
}

variable "database_name" {
  type    = string
  default = "ABBVIE_DATAOPS_DEV"
}

variable "warehouse_name" {
  type    = string
  default = "ABBVIE_DATAOPS_WH"
}

variable "deploy_role_name" {
  type    = string
  default = "ABBVIE_DATAOPS_DEPLOY"
}

variable "github_subject" {
  type        = string
  description = "GitHub OIDC subject claim for the service user (e.g. repo:org/repo:ref:refs/heads/main)"
  default     = "repo:sfc-gh-palapaty/abbvie-dataops-sdk:environment:dev"
}

resource "snowflake_warehouse" "wh" {
  name           = var.warehouse_name
  warehouse_size = "XSMALL"
  auto_suspend   = 60
  auto_resume    = true
}

resource "snowflake_database" "db" {
  name    = var.database_name
  comment = "Abbvie DataOps PoC governed database"
}

resource "snowflake_schema" "curated" {
  database = snowflake_database.db.name
  name     = "CURATED"
}

resource "snowflake_schema" "schemachange" {
  database = snowflake_database.db.name
  name     = "SCHEMACHANGE"
  comment  = "schemachange CHANGE_HISTORY tracking table lives here"
}

resource "snowflake_role" "deploy" {
  name    = var.deploy_role_name
  comment = "Role assumed by GitHub Actions CI to deploy DCM changes"
}

resource "snowflake_database_grant" "deploy_db" {
  database_name = snowflake_database.db.name
  privilege     = "USAGE"
  roles         = [snowflake_role.deploy.name]
}

resource "snowflake_schema_grant" "deploy_schemas" {
  for_each      = toset([snowflake_schema.curated.name, snowflake_schema.schemachange.name])
  database_name = snowflake_database.db.name
  schema_name   = each.value
  privilege     = "ALL"
  roles         = [snowflake_role.deploy.name]
}

resource "snowflake_warehouse_grant" "deploy_wh" {
  warehouse_name = snowflake_warehouse.wh.name
  privilege      = "USAGE"
  roles          = [snowflake_role.deploy.name]
}

# OIDC service user per Snowflake CI/CD guide:
# https://www.snowflake.com/en/developers/guides/configure-cicd-integrations-with-snowflake/
#
# Snowflake-Labs provider does not yet expose WORKLOAD_IDENTITY natively, so we run the SQL
# manually (see docs/SNOWFLAKE_OIDC_SETUP.sql). Keeping a placeholder role grant here for clarity.

output "deploy_role" {
  value = snowflake_role.deploy.name
}

output "warehouse" {
  value = snowflake_warehouse.wh.name
}

output "database" {
  value = snowflake_database.db.name
}
