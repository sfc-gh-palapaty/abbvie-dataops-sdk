resource "random_password" "rds" {
  length  = 24
  special = false
}

resource "aws_db_subnet_group" "suitecrm" {
  name       = "${var.name_prefix}-suitecrm"
  subnet_ids = local.subnet_ids
}

resource "aws_security_group" "suitecrm_db" {
  name        = "${var.name_prefix}-suitecrm-db"
  description = "MySQL access for SuiteCRM ECS tasks"
  vpc_id      = local.vpc_id
}

resource "aws_security_group" "suitecrm_app" {
  name        = "${var.name_prefix}-suitecrm-app"
  description = "SuiteCRM Fargate task SG"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet (PoC only)"
  }
}

resource "aws_security_group_rule" "suitecrm_db_from_app" {
  security_group_id        = aws_security_group.suitecrm_db.id
  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.suitecrm_app.id
}

resource "aws_db_instance" "suitecrm" {
  identifier              = "${var.name_prefix}-suitecrm"
  engine                  = "mysql"
  engine_version          = "8.0"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_encrypted       = true
  username                = var.rds_master_username
  password                = random_password.rds.result
  db_name                 = "suitecrm"
  db_subnet_group_name    = aws_db_subnet_group.suitecrm.name
  vpc_security_group_ids  = [aws_security_group.suitecrm_db.id]
  skip_final_snapshot     = true
  publicly_accessible     = false
  backup_retention_period = 1
  apply_immediately       = true
}

resource "aws_secretsmanager_secret" "suitecrm_db" {
  name                    = "${var.name_prefix}/suitecrm/db"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "suitecrm_db" {
  secret_id = aws_secretsmanager_secret.suitecrm_db.id
  secret_string = jsonencode({
    host     = aws_db_instance.suitecrm.address
    port     = aws_db_instance.suitecrm.port
    username = var.rds_master_username
    password = random_password.rds.result
    database = "suitecrm"
  })
}

resource "aws_ecr_repository" "suitecrm" {
  name                 = "${var.name_prefix}/suitecrm"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.name_prefix}-ecs-task-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_exec_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_exec_secrets" {
  name = "${var.name_prefix}-ecs-exec-secrets"
  role = aws_iam_role.ecs_task_execution.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["secretsmanager:GetSecretValue"],
      Resource = aws_secretsmanager_secret.suitecrm_db.arn
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "ecs_task_inline" {
  name = "${var.name_prefix}-ecs-task-inline"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          aws_s3_bucket.raw.arn,
          "${aws_s3_bucket.raw.arn}/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = ["secretsmanager:GetSecretValue"],
        Resource = aws_secretsmanager_secret.suitecrm_db.arn
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "suitecrm" {
  name              = "/ecs/${var.name_prefix}/suitecrm"
  retention_in_days = 14
}
