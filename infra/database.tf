resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = local.name }
}

resource "aws_db_parameter_group" "main" {
  name_prefix = "${local.name}-pg16-"
  family      = "postgres16"

  parameter {
    name  = "timezone"
    value = "UTC"
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_db_instance" "main" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  db_name  = "healthx"
  username = "healthx"
  password = random_password.db.result

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  multi_az               = var.db_multi_az
  publicly_accessible    = false

  backup_retention_period = var.db_backup_retention_days
  backup_window           = "18:30-19:30" # ~midnight IST
  maintenance_window      = "Mon:19:45-Mon:20:45"
  copy_tags_to_snapshot   = true

  deletion_protection       = var.db_deletion_protection
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final"

  performance_insights_enabled = true
  auto_minor_version_upgrade   = true

  tags = { Name = local.name }
}
