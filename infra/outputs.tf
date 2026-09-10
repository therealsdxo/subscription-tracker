output "api_url" {
  description = "Public base URL of the API"
  value       = local.enable_https ? "https://${var.domain_name}" : "http://${aws_lb.api.dns_name}"
}

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "migrate_task_definition" {
  description = "Run this before rolling a new API version"
  value       = aws_ecs_task_definition.migrate.arn_without_revision
}

output "rds_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "acm_certificate_validation_records" {
  description = "Create these DNS records to validate the ACM cert (when domain_name is set)"
  value = local.enable_https ? [
    for o in aws_acm_certificate.api[0].domain_validation_options : {
      name  = o.resource_record_name
      type  = o.resource_record_type
      value = o.resource_record_value
    }
  ] : []
}
