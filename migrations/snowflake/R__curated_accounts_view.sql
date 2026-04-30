-- Repeatable migration: convenience view that joins curated.ACCOUNTS to the most recent
-- bronze Iceberg snapshot via Snowflake external table (configured separately as one-off).
USE SCHEMA CURATED;

CREATE OR REPLACE VIEW V_ACCOUNTS_GOVERNED AS
SELECT
    a.ID,
    a.NAME,
    a.INDUSTRY,
    a.ANNUAL_REVENUE,
    a.EMAIL,
    a.CREATED_AT,
    a.UPDATED_AT,
    'snowflake.curated.accounts' AS GOVERNED_LINEAGE_NODE
FROM ACCOUNTS a;
