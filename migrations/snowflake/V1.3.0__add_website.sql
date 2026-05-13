-- Demo #2 migration. Intentionally added WITHOUT updating
-- manifests/schemas/snowflake/accounts.json on this commit. The PR
-- governance gate must block the PR until the contract is updated.
USE SCHEMA CURATED;
ALTER TABLE ACCOUNTS ADD COLUMN WEBSITE VARCHAR;
