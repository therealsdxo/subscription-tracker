terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State backend is intentionally not configured here. Configure an S3 backend
  # (with a DynamoDB lock table) per environment before `terraform apply`:
  #
  #   terraform init -backend-config=backend.hcl
  #
  # For local `terraform validate` use `terraform init -backend=false`.
}
