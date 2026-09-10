variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Resource name prefix"
  type        = string
  default     = "healthx"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

# --- database -----------------------------------------------------------

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ (leave off for v1 to control cost)"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  type    = number
  default = 14
}

variable "db_deletion_protection" {
  type    = bool
  default = true
}

# --- api service ------------------------------------------------------

variable "api_image_tag" {
  description = "Image tag to deploy from the ECR repo"
  type        = string
  default     = "latest"
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "api_min_count" {
  type    = number
  default = 1
}

variable "api_max_count" {
  type    = number
  default = 4
}

variable "cors_origins" {
  description = "Allowed browser origins for the API (the frontend URL)"
  type        = string
  default     = "http://localhost:3000"
}

# --- tls / dns -------------------------------------------------------

variable "domain_name" {
  description = "Optional FQDN for the API. When set, an ACM cert + HTTPS listener are created; otherwise the ALB serves plain HTTP (put it behind a TLS-terminating layer)."
  type        = string
  default     = ""
}

# --- observability -------------------------------------------------

variable "alarm_email" {
  description = "Optional address subscribed to the CloudWatch alarm SNS topic"
  type        = string
  default     = ""
}
