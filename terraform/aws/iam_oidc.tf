data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = var.github_subject_claims
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.name_prefix}-gha-deploy"
  description        = "Assumed by GitHub Actions via OIDC for ${var.github_owner}/${var.github_repo}"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

data "aws_iam_policy_document" "github_actions_inline" {
  statement {
    sid    = "S3DataPlanes"
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
    sid    = "EMRServerlessSubmit"
    effect = "Allow"
    actions = [
      "emr-serverless:StartApplication",
      "emr-serverless:StartJobRun",
      "emr-serverless:GetJobRun",
      "emr-serverless:CancelJobRun",
      "emr-serverless:ListJobRuns",
      "emr-serverless:GetApplication",
      "emr-serverless:ListApplications"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PassEMRRuntimeRole"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.emr_runtime.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["emr-serverless.amazonaws.com"]
    }
  }

  statement {
    sid    = "ECRPushPull"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECSUpdateService"
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService",
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
      "ecs:RunTask",
      "ecs:DescribeTasks",
      "ecs:ListTasks"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PassECSExecRoles"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]
  }

  statement {
    sid       = "SecretsRead"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = ["arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:${var.name_prefix}/*"]
  }

  statement {
    sid    = "GlueRead"
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartitions",
      "glue:CreateTable",
      "glue:UpdateTable"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_inline" {
  name   = "${var.name_prefix}-gha-deploy-inline"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions_inline.json
}
