data "aws_iam_policy_document" "emr_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["emr-serverless.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "emr_runtime" {
  name               = "${var.name_prefix}-emr-runtime"
  assume_role_policy = data.aws_iam_policy_document.emr_assume.json
}

data "aws_iam_policy_document" "emr_runtime_inline" {
  statement {
    sid    = "S3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = [
      aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*",
      aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*",
      aws_s3_bucket.lineage.arn, "${aws_s3_bucket.lineage.arn}/*",
      aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"
    ]
  }

  statement {
    sid    = "GlueIcebergCatalog"
    effect = "Allow"
    actions = [
      "glue:*Database*",
      "glue:*Table*",
      "glue:*Partition*",
      "glue:GetCatalogImportStatus"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "Logs"
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups", "logs:DescribeLogStreams"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "emr_runtime_inline" {
  name   = "${var.name_prefix}-emr-runtime-inline"
  role   = aws_iam_role.emr_runtime.id
  policy = data.aws_iam_policy_document.emr_runtime_inline.json
}

resource "aws_emrserverless_application" "spark" {
  name          = "${var.name_prefix}-spark"
  release_label = "emr-7.2.0"
  type          = "spark"

  initial_capacity {
    initial_capacity_type = "Driver"
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = "2 vCPU"
        memory = "8 GB"
      }
    }
  }

  initial_capacity {
    initial_capacity_type = "Executor"
    initial_capacity_config {
      worker_count = 2
      worker_configuration {
        cpu    = "2 vCPU"
        memory = "8 GB"
      }
    }
  }

  maximum_capacity {
    cpu    = "16 vCPU"
    memory = "64 GB"
  }

  network_configuration {
    subnet_ids         = local.subnet_ids
    security_group_ids = [aws_security_group.datahub_access.id]
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }
}
