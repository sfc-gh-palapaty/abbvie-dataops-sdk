resource "aws_secretsmanager_secret" "datahub" {
  name                    = "${var.name_prefix}/datahub/endpoints"
  description             = "DataHub GMS + Marquez URLs (set after EC2 bring-up)"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "datahub" {
  secret_id = aws_secretsmanager_secret.datahub.id
  secret_string = jsonencode({
    datahub_gms_url      = "http://${data.aws_instance.datahub.private_ip}:8000"
    datahub_frontend_url = "http://${data.aws_instance.datahub.private_ip}:8080"
    openlineage_url      = "http://${data.aws_instance.datahub.private_ip}:5000"
    datahub_token        = ""
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "snowflake" {
  name                    = "${var.name_prefix}/snowflake/connection"
  description             = "Snowflake account + service-user details (populated manually)"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "snowflake_placeholder" {
  secret_id = aws_secretsmanager_secret.snowflake.id
  secret_string = jsonencode({
    account   = "REPLACE.region.cloud"
    user      = "GH_CICD_USER"
    role      = "ABBVIE_DATAOPS_DEPLOY"
    warehouse = "ABBVIE_DATAOPS_WH"
    database  = "ABBVIE_DATAOPS_DEV"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
