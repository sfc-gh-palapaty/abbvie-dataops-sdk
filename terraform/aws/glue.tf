resource "aws_glue_catalog_database" "bronze" {
  name        = "${replace(var.name_prefix, "-", "_")}_bronze"
  description = "Bronze (raw) Iceberg tables for DataOps PoC"
}

resource "aws_glue_catalog_database" "curated" {
  name        = "${replace(var.name_prefix, "-", "_")}_curated"
  description = "Curated (silver/gold) Iceberg tables for DataOps PoC"
}
