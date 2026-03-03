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
