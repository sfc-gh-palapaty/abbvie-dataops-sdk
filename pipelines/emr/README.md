# EMR Serverless transform

`transform_accounts.py` reads SuiteCRM bronze parquet and writes the curated Iceberg
table (`glue_catalog.<db>.accounts`). The job is submitted by
`.github/workflows/emr-deploy.yml` with the OpenLineage Spark listener attached:

```text
--jars s3://.../openlineage-spark.jar
--conf spark.extraListeners=io.openlineage.spark.agent.OpenLineageSparkListener
--conf spark.openlineage.transport.type=http
--conf spark.openlineage.transport.url=$OPENLINEAGE_URL
--conf spark.openlineage.namespace=abbvie.glue
```

Iceberg is configured via the Glue catalog implementation:

```text
--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
--conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog
--conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog
--conf spark.sql.catalog.glue_catalog.warehouse=s3://${S3_CURATED_BUCKET}/
```
