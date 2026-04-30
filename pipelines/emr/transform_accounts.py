"""EMR Serverless PySpark job: bronze (parquet) -> curated (Iceberg / Glue Catalog).

Reads SuiteCRM extracts from `--input` (S3 raw), normalizes the schema,
writes an Iceberg table registered in Glue (`glue_catalog.<db>.<table>`).
The OpenLineage Spark listener -- wired up via spark-submit args in the
GitHub Actions workflow -- emits START/COMPLETE events to Marquez automatically.
"""

from __future__ import annotations

import argparse
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


SCHEMA = StructType(
    [
        StructField("id", StringType(), nullable=False),
        StructField("name", StringType(), nullable=False),
        StructField("industry", StringType(), nullable=True),
        StructField("annual_revenue", DecimalType(18, 2), nullable=True),
        StructField("email", StringType(), nullable=True),
        StructField("created_at", TimestampType(), nullable=False),
        StructField("updated_at", TimestampType(), nullable=False),
    ]
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="s3://.../suitecrm/accounts/")
    p.add_argument("--output", required=True, help="s3://.../accounts/")
    p.add_argument("--glue-database", required=True)
    p.add_argument("--glue-table", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    spark = (
        SparkSession.builder.appName("abbvie-dataops-transform-accounts")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    raw = (
        spark.read.option("mergeSchema", "true")
        .parquet(args.input)
    )

    cleaned = (
        raw.select(
            F.col("id").cast(StringType()).alias("id"),
            F.col("name").cast(StringType()).alias("name"),
            F.col("industry").cast(StringType()).alias("industry"),
            F.col("annual_revenue").cast(DecimalType(18, 2)).alias("annual_revenue"),
            F.lower(F.col("email")).alias("email"),
            F.col("created_at").cast(TimestampType()).alias("created_at"),
            F.col("updated_at").cast(TimestampType()).alias("updated_at"),
        )
        .where(F.col("id").isNotNull())
        .where(F.col("name").isNotNull())
        .dropDuplicates(["id"])
    )

    print(f"cleaned row count = {cleaned.count()}")
    cleaned.printSchema()

    table_fqn = f"glue_catalog.{args.glue_database}.{args.glue_table}"

    (
        cleaned.writeTo(table_fqn)
        .using("iceberg")
        .tableProperty("location", args.output)
        .tableProperty("write.format.default", "parquet")
        .createOrReplace()
    )

    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
