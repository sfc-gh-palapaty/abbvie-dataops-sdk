variable "aws_region" {
  type        = string
  description = "AWS region for all PoC resources"
  default     = "us-west-2"
}

variable "environment" {
  type        = string
  description = "Environment name (dev|stage|prod)"
  default     = "dev"
}

variable "name_prefix" {
  type        = string
  description = "Common prefix for all named resources"
  default     = "abbvie-dataops-poc"
}

variable "github_owner" {
  type        = string
  description = "GitHub org or user that owns the repo allowed to assume the OIDC role"
  default     = "sfc-gh-palapaty"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name"
  default     = "abbvie-dataops-poc-aws"
}

variable "github_subject_claims" {
  type        = list(string)
  description = "Allowed GitHub OIDC subject claim patterns"
  default = [
    "repo:sfc-gh-palapaty/abbvie-dataops-poc-aws:ref:refs/heads/main",
    "repo:sfc-gh-palapaty/abbvie-dataops-poc-aws:pull_request",
    "repo:sfc-gh-palapaty/abbvie-dataops-poc-aws:environment:dev"
  ]
}

variable "datahub_ec2_instance_id" {
  type        = string
  description = "EC2 instance ID hosting DataHub + Marquez (provided by user)"
  default     = "i-0165db8e63bcdb1d3"
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID to deploy into. Leave empty to use the account's default VPC."
  default     = ""
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for EMR Serverless network config and ECS tasks. Leave empty to autodiscover from default VPC."
  default     = []
}

variable "rds_master_username" {
  type        = string
  description = "Master username for SuiteCRM RDS MySQL"
  default     = "suitecrm"
}
