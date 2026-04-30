-- Initial objects in the curated zone for the AbbVie DataOps PoC.
-- Mirrors the Snowflake schemachange + GitHub Actions guide pattern:
--   https://www.snowflake.com/en/developers/guides/devops-dcm-schemachange-github/

CREATE SCHEMA IF NOT EXISTS CURATED;

USE SCHEMA CURATED;

CREATE TABLE IF NOT EXISTS ACCOUNTS (
    ID              VARCHAR        NOT NULL,
    NAME            VARCHAR        NOT NULL,
    INDUSTRY        VARCHAR        NULL,
    ANNUAL_REVENUE  NUMBER(18, 2)  NULL,
    CREATED_AT      TIMESTAMP_NTZ  NOT NULL,
    UPDATED_AT      TIMESTAMP_NTZ  NOT NULL,
    CONSTRAINT PK_ACCOUNTS PRIMARY KEY (ID)
);

COMMENT ON TABLE ACCOUNTS IS 'Curated CRM accounts -- governed by abbvie-dataops manifest manifests/snowflake-curated.yaml';
