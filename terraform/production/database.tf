locals {
  DATABASE_URL = sensitive("postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}")
}

resource "random_password" "db_password" {
  length  = 32
  special = true
  # Avoid characters that might cause issues in connection strings or URL parsing
  override_special = "!$%&*()-_=+"
}

resource "aws_db_subnet_group" "main" {
  name       = "hexagone-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier     = "hexagone-postgres"
  engine         = "postgres"
  engine_version = "17.4"
  instance_class = "db.t4g.micro"

  # Database configuration
  db_name  = "postgres"
  username = "postgres"
  password = random_password.db_password.result

  # Storage configuration
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup configuration
  backup_retention_period = 1
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  # Monitoring and logging
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  # Performance Insights
  performance_insights_enabled = false

  # Deletion protection removed until we are settled on the schema.
  deletion_protection = false
  skip_final_snapshot = true

  # Apply changes immediately (for development, set to false when we go to production)
  apply_immediately = true
}

resource "aws_iam_role" "rds_monitoring" {
  name = "HexagoneRDSMonitoringRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
