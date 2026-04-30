resource "aws_s3_bucket" "raw" {
  bucket        = "${var.name_prefix}-raw-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "curated" {
  bucket        = "${var.name_prefix}-curated-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "lineage" {
  bucket        = "${var.name_prefix}-lineage-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${var.name_prefix}-artifacts-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = {
    raw       = aws_s3_bucket.raw.id
    curated   = aws_s3_bucket.curated.id
    lineage   = aws_s3_bucket.lineage.id
    artifacts = aws_s3_bucket.artifacts.id
  }

  bucket = each.value

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = {
    raw       = aws_s3_bucket.raw.id
    curated   = aws_s3_bucket.curated.id
    lineage   = aws_s3_bucket.lineage.id
    artifacts = aws_s3_bucket.artifacts.id
  }

  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
