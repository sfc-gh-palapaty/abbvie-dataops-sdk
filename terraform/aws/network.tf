data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_vpc" "default" {
  count   = var.vpc_id == "" ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = length(var.private_subnet_ids) == 0 ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [var.vpc_id == "" ? data.aws_vpc.default[0].id : var.vpc_id]
  }
}

locals {
  vpc_id     = var.vpc_id == "" ? data.aws_vpc.default[0].id : var.vpc_id
  subnet_ids = length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : data.aws_subnets.default[0].ids
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

data "aws_instance" "datahub" {
  instance_id = var.datahub_ec2_instance_id
}

resource "aws_security_group" "datahub_access" {
  name        = "${var.name_prefix}-datahub-access"
  description = "Allow EMR Serverless and ECS to reach DataHub GMS / Marquez on the EC2"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "datahub_ingress_gms" {
  security_group_id        = data.aws_instance.datahub.vpc_security_group_ids[0]
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.datahub_access.id
  description              = "DataHub frontend from PoC workloads"
}

resource "aws_security_group_rule" "datahub_ingress_gms_api" {
  security_group_id        = data.aws_instance.datahub.vpc_security_group_ids[0]
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.datahub_access.id
  description              = "DataHub GMS REST from PoC workloads"
}

resource "aws_security_group_rule" "datahub_ingress_marquez" {
  security_group_id        = data.aws_instance.datahub.vpc_security_group_ids[0]
  type                     = "ingress"
  from_port                = 5000
  to_port                  = 5000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.datahub_access.id
  description              = "Marquez API from PoC workloads"
}
