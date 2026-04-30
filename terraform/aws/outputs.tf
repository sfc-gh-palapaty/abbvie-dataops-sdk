output "github_actions_role_arn" {
  description = "Set this as the GitHub repo variable AWS_GHA_ROLE_ARN"
  value       = aws_iam_role.github_actions.arn
}

output "emr_serverless_application_id" {
  value = aws_emrserverless_application.spark.id
}

output "emr_runtime_role_arn" {
  value = aws_iam_role.emr_runtime.arn
}

output "s3_buckets" {
  value = {
    raw       = aws_s3_bucket.raw.bucket
    curated   = aws_s3_bucket.curated.bucket
    lineage   = aws_s3_bucket.lineage.bucket
    artifacts = aws_s3_bucket.artifacts.bucket
  }
}

output "glue_databases" {
  value = {
    bronze  = aws_glue_catalog_database.bronze.name
    curated = aws_glue_catalog_database.curated.name
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.suitecrm.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "suitecrm_app_security_group_id" {
  value = aws_security_group.suitecrm_app.id
}

output "suitecrm_db_endpoint" {
  value = aws_db_instance.suitecrm.endpoint
}

output "suitecrm_db_secret_arn" {
  value = aws_secretsmanager_secret.suitecrm_db.arn
}

output "datahub_endpoints_secret_arn" {
  value = aws_secretsmanager_secret.datahub.arn
}

output "datahub_private_ip" {
  value = data.aws_instance.datahub.private_ip
}

output "subnet_ids" {
  value = local.subnet_ids
}
