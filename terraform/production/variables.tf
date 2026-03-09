variable "domain_name" {
  description = "Domain name for the CloudFront distribution and ACM certificate"
  type        = string
  default     = "hexagone.one"
}

variable "lambda_image_tag" {
  description = "Docker image tag for the Lambda function"
  type        = string
  default     = "latest"
}

variable "tailscale_auth_key" {
  description = "Tailscale pre-authentication key for the subnet router"
  type        = string
  sensitive   = true
}
