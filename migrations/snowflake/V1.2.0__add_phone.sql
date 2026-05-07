-- Demo migration intentionally added WITHOUT updating
-- manifests/schemas/snowflake/accounts.json. The PR governance gate
-- must block this PR until the schema contract is updated.
USE SCHEMA CURATED;
ALTER TABLE ACCOUNTS ADD COLUMN PHONE VARCHAR;
