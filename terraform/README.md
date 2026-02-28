# Terraform — Hexagone Infrastructure

Provisions AWS infrastructure for the Hexagone frontend:

- **S3 bucket** (`hexagone-web`) — stores built static files, private access only
- **CloudFront distribution** — CDN with HTTPS, HTTP/2+3, and SPA routing
- **ACM certificate** — TLS for `haxagone.com` (DNS-validated, us-east-1)
- **Route53** (optional) — DNS zone and records when `enable_dns = true`

## Prerequisites

- [Terraform >= 1.6.0](https://developer.hashicorp.com/terraform/install)
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- S3 bucket `hexagone-terraform-state` for remote state (create manually once)

## Getting Started

```bash
cd terraform/production
terraform init
terraform plan
terraform apply
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `eu-west-1` | AWS region for S3 and other regional resources |
| `domain_name` | `haxagone.com` | Domain for CloudFront and ACM certificate |
| `enable_dns` | `false` | Create Route53 zone and DNS records |

## Deploying Frontend Assets

After `terraform apply` has created the infrastructure:

```bash
# 1. Build the frontend
pnpm -C apps/web build

# 2. Sync built files to S3 (--delete removes old files no longer in the build)
aws s3 sync apps/web/dist/ s3://hexagone-web --delete

# 3. Invalidate CloudFront cache so edges serve the new version
aws cloudfront create-invalidation \
  --distribution-id $(terraform -chdir=terraform/production output -raw cloudfront_distribution_id) \
  --paths "/*"
```

## DNS Setup

If managing DNS outside AWS (e.g. at a registrar), set `enable_dns = false` (the default) and:

1. Create the CNAME record shown in the ACM console to validate the certificate
2. Point your domain to the CloudFront distribution domain name (`dXXXXXXXXX.cloudfront.net`)

If managing DNS in AWS, set `enable_dns = true` — Terraform will create the Route53 zone, validation records, and A/AAAA alias records. Set the nameservers from `terraform output nameservers` at your registrar.
