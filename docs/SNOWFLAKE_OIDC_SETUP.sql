-- Snowflake-side OIDC service user for the AbbVie DataOps PoC.
-- Run as ACCOUNTADMIN once. Reference:
--   https://www.snowflake.com/en/developers/guides/configure-cicd-integrations-with-snowflake/

USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS ABBVIE_DATAOPS_DEPLOY;

GRANT USAGE ON WAREHOUSE ABBVIE_DATAOPS_WH TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT USAGE ON DATABASE ABBVIE_DATAOPS_DEV TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT ALL ON SCHEMA ABBVIE_DATAOPS_DEV.CURATED TO ROLE ABBVIE_DATAOPS_DEPLOY;
GRANT ALL ON SCHEMA ABBVIE_DATAOPS_DEV.SCHEMACHANGE TO ROLE ABBVIE_DATAOPS_DEPLOY;

-- OIDC service user. Replace SUBJECT with your fork if different.
CREATE OR REPLACE USER GH_CICD_USER
  TYPE = SERVICE
  WORKLOAD_IDENTITY = (
    TYPE = OIDC
    ISSUER = 'https://token.actions.githubusercontent.com'
    SUBJECT = 'repo:sfc-gh-palapaty/abbvie-dataops-sdk:ref:refs/heads/main'
  )
  DEFAULT_ROLE = ABBVIE_DATAOPS_DEPLOY
  DEFAULT_WAREHOUSE = ABBVIE_DATAOPS_WH;

GRANT ROLE ABBVIE_DATAOPS_DEPLOY TO USER GH_CICD_USER;

-- Optional: a second user to allow PR previews from non-main branches.
CREATE OR REPLACE USER GH_CICD_USER_PR
  TYPE = SERVICE
  WORKLOAD_IDENTITY = (
    TYPE = OIDC
    ISSUER = 'https://token.actions.githubusercontent.com'
    SUBJECT = 'repo:sfc-gh-palapaty/abbvie-dataops-sdk:pull_request'
  )
  DEFAULT_ROLE = ABBVIE_DATAOPS_DEPLOY
  DEFAULT_WAREHOUSE = ABBVIE_DATAOPS_WH;

GRANT ROLE ABBVIE_DATAOPS_DEPLOY TO USER GH_CICD_USER_PR;
