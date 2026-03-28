output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (used for cache invalidation)"
  value       = aws_cloudfront_distribution.web.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.web.domain_name
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.web.id
}

output "nameservers" {
  description = "Route53 nameservers (set these at your registrar)"
  value       = aws_route53_zone.main.name_servers
}

output "ecr_repository_url" {
  description = "ECR repository URL for the backend Lambda image"
  value       = aws_ecr_repository.backend.repository_url
}

output "api_gateway_url" {
  description = "API Gateway default URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "db_ops_lambda_function_name" {
  description = "DB Ops Lambda function name"
  value       = aws_lambda_function.db_ops.function_name
}

output "upload_processor_lambda_function_name" {
  description = "Upload Processor Lambda function name"
  value       = aws_lambda_function.upload_processor.function_name
}

output "uploads_s3_bucket_name" {
  description = "S3 bucket name for GPX uploads"
  value       = aws_s3_bucket.uploads.id
}

output "tailscale_instance_id" {
  description = "Tailscale subnet router instance ID (for SSM Session Manager)"
  value       = aws_instance.tailscale.id
}

output "db_connection_command" {
  description = "Command to connect to the database via Tailscale"
  value       = "psql \"postgresql://${aws_db_instance.main.username}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}\""
  sensitive   = true
}

output "database_host" {
  description = "RDS instance endpoint hostname"
  value       = aws_db_instance.main.address
}

output "database_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_user" {
  description = "RDS master username"
  value       = aws_db_instance.main.username
}

output "database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "db_password" {
  description = "Database password (sensitive)"
  value       = random_password.db_password.result
  sensitive   = true
}
