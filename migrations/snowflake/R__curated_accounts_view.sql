-- Repeatable migration: BI-safe governance overlay view. Applies the
-- tokenization policy from manifests/policies/snowflake/curated-accounts.yaml:
--   - EMAIL    -> EMAIL_TOKENIZED        (hash truncation)
--   - PHONE    -> PHONE_TOKENIZED        (last 4 only)
--   - WEBSITE  -> WEBSITE_DOMAIN_ONLY    (strip protocol + path)
--   - ANNUAL_REVENUE -> ANNUAL_REVENUE_BUCKETED (banding)
-- Replays on every deploy so newly added columns flow through automatically.
USE SCHEMA CURATED;

CREATE OR REPLACE VIEW V_ACCOUNTS_GOVERNED AS
SELECT
    a.ID,
    a.NAME,
    a.INDUSTRY,
    CASE
        WHEN a.ANNUAL_REVENUE >= 1000000000 THEN '1B+'
        WHEN a.ANNUAL_REVENUE >= 100000000  THEN '100M-1B'
        WHEN a.ANNUAL_REVENUE >= 10000000   THEN '10M-100M'
        WHEN a.ANNUAL_REVENUE IS NULL       THEN NULL
        ELSE '<10M'
    END                                                       AS ANNUAL_REVENUE_BUCKETED,
    LEFT(SHA2(a.EMAIL, 256), 16)                              AS EMAIL_TOKENIZED,
    CASE WHEN a.PHONE   IS NULL THEN NULL ELSE '***-***-' || RIGHT(a.PHONE, 4) END  AS PHONE_TOKENIZED,
    REGEXP_REPLACE(REGEXP_REPLACE(a.WEBSITE, '^https?://', ''), '/.*$', '')         AS WEBSITE_DOMAIN_ONLY,
    a.CREATED_AT,
    a.UPDATED_AT,
    'snowflake.curated.accounts' AS GOVERNED_LINEAGE_NODE
FROM ACCOUNTS a;
