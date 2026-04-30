# Snowflake migrations (schemachange)

Versioned (`V*.sql`) and repeatable (`R*.sql`) scripts applied by
`schemachange` from `.github/workflows/snowflake-deploy.yml`.

| File | Purpose |
|---|---|
| `V1.1.1__initial_objects.sql` | `CURATED` schema + `ACCOUNTS` table baseline |
| `V1.1.2__add_email.sql` | Adds `EMAIL` column + unique constraint |
| `R__curated_accounts_view.sql` | Repeatable governed-view definition |

The DataOps SDK gate (manifest `manifests/snowflake-curated.yaml`) runs **after**
schemachange to verify that the resulting table matches `manifests/schemas/snowflake/accounts.json`.
