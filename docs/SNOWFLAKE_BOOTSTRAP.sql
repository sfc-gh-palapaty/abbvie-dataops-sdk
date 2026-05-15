-- ============================================================================
-- AbbVie DataOps PoC -- Snowflake account bootstrap (one-shot)
--
-- Account: <SNOWFLAKE_ACCOUNT> (locator <SNOWFLAKE_ACCOUNT_LOCATOR>)
-- Run this entire script ONCE as ACCOUNTADMIN in Snowsight (or via snow CLI).
-- It is idempotent: safe to re-run.
--
-- After this finishes, the GitHub Actions workflows in
-- sfc-gh-palapaty/abbvie-dataops-sdk can authenticate via OIDC as GH_CICD_USER.
-- References:
--   https://www.snowflake.com/en/developers/guides/configure-cicd-integrations-with-snowflake/
--   https://www.snowflake.com/en/developers/guides/devops-dcm-schemachange-github/
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- ---------------------------------------------------------------------------
-- 1. Database, schemas, warehouse
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS ABBVIE_DATAOPS_DEV
    COMMENT = 'AbbVie DataOps PoC governed database';

CREATE SCHEMA IF NOT EXISTS ABBVIE_DATAOPS_DEV.CURATED;

CREATE SCHEMA IF NOT EXISTS ABBVIE_DATAOPS_DEV.SCHEMACHANGE
    COMMENT = 'schemachange CHANGE_HISTORY tracking table lives here';

CREATE WAREHOUSE IF NOT EXISTS ABBVIE_DATAOPS_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'AbbVie DataOps PoC CI/CD compute';

-- ---------------------------------------------------------------------------
-- 2. Deploy role + grants (used by both schemachange and the SDK gate)
-- ---------------------------------------------------------------------------
CREATE ROLE IF NOT EXISTS ABBVIE_DATAOPS_DEPLOY
    COMMENT = 'Role assumed by GitHub Actions CI to deploy DCM changes';

GRANT USAGE ON WAREHOUSE ABBVIE_DATAOPS_WH        TO ROLE ABBVIE_DATAOPS_DEPLOY;
-- Database-level grants. CREATE SCHEMA is required because schemachange's
-- V1.1.1__initial_objects.sql executes `CREATE SCHEMA IF NOT EXISTS CURATED`.
-- MODIFY/MONITOR keep ALTER DATABASE-style operations available to CI.
GRANT USAGE, MODIFY, MONITOR, CREATE SCHEMA
    ON DATABASE ABBVIE_DATAOPS_DEV
    TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT ALL   ON SCHEMA    ABBVIE_DATAOPS_DEV.CURATED      TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT ALL   ON SCHEMA    ABBVIE_DATAOPS_DEV.SCHEMACHANGE TO ROLE ABBVIE_DATAOPS_DEPLOY;

-- Future-proof grants so newly created objects inside CURATED are visible to the deploy role
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES
    ON FUTURE TABLES IN SCHEMA ABBVIE_DATAOPS_DEV.CURATED
    TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT SELECT, REFERENCES
    ON FUTURE VIEWS IN SCHEMA ABBVIE_DATAOPS_DEV.CURATED
    TO ROLE ABBVIE_DATAOPS_DEPLOY;

-- Allow the deploy role to read/manage future objects in SCHEMACHANGE so schemachange can
-- create + update its CHANGE_HISTORY tracking table.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON FUTURE TABLES IN SCHEMA ABBVIE_DATAOPS_DEV.SCHEMACHANGE
    TO ROLE ABBVIE_DATAOPS_DEPLOY;

-- ---------------------------------------------------------------------------
-- 3. OIDC service users for GitHub Actions
--
-- IMPORTANT: GitHub stamps the OIDC JWT subject based on the *workflow trigger
-- context*. snowflake-deploy.yml declares `environment: dev`, so the subject
-- arrives as `repo:<owner>/<repo>:environment:dev`, NOT
-- `:ref:refs/heads/main`. The main-branch user therefore matches on the
-- environment claim (the only safe one when an Actions environment is used).
-- See: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect#example-subject-claims
--
--   Repo: sfc-gh-palapaty/abbvie-dataops-sdk
-- ---------------------------------------------------------------------------
CREATE OR REPLACE USER GH_CICD_USER
    TYPE = SERVICE
    WORKLOAD_IDENTITY = (
        TYPE = OIDC
        ISSUER = 'https://token.actions.githubusercontent.com'
        SUBJECT = 'repo:sfc-gh-palapaty/abbvie-dataops-sdk:environment:dev'
    )
    DEFAULT_ROLE = ABBVIE_DATAOPS_DEPLOY
    DEFAULT_WAREHOUSE = ABBVIE_DATAOPS_WH
    COMMENT = 'GitHub Actions OIDC service user for `environment: dev` deploys';

GRANT ROLE ABBVIE_DATAOPS_DEPLOY TO USER GH_CICD_USER;

-- PR previews (workflows triggered by `pull_request`, no environment set)
CREATE OR REPLACE USER GH_CICD_USER_PR
    TYPE = SERVICE
    WORKLOAD_IDENTITY = (
        TYPE = OIDC
        ISSUER = 'https://token.actions.githubusercontent.com'
        SUBJECT = 'repo:sfc-gh-palapaty/abbvie-dataops-sdk:pull_request'
    )
    DEFAULT_ROLE = ABBVIE_DATAOPS_DEPLOY
    DEFAULT_WAREHOUSE = ABBVIE_DATAOPS_WH
    COMMENT = 'GitHub Actions OIDC service user for PR runs';

GRANT ROLE ABBVIE_DATAOPS_DEPLOY TO USER GH_CICD_USER_PR;

-- ---------------------------------------------------------------------------
-- 4. Sanity checks (run after the above completes)
-- ---------------------------------------------------------------------------
SHOW USERS LIKE 'GH_CICD_USER%';
SHOW GRANTS TO ROLE ABBVIE_DATAOPS_DEPLOY;
DESCRIBE WAREHOUSE ABBVIE_DATAOPS_WH;
SHOW SCHEMAS IN DATABASE ABBVIE_DATAOPS_DEV;
