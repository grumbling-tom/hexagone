# Terraform — Hexagone Infrastructure

Provisions AWS infrastructure for Hexagone:

- **S3 bucket** (`hexagone-web`) — stores built static files, private access only
- **CloudFront distribution** — CDN with HTTPS, HTTP/2+3, SPA routing, and API proxy (`/api/*`)
- **ACM certificate** — TLS for `hexagone.one` (DNS-validated, us-east-1)
- **Route53** (optional) — DNS zone and records when `enable_dns = true`
- **ECR repository** (`hexagone-backend`) — Docker images for the backend Lambda
- **Lambda function** (`hexagone-backend`) — FastAPI backend via Mangum
- **API Gateway HTTP API** — routes requests to the Lambda function

## Prerequisites

- [Terraform >= 1.6.0](https://developer.hashicorp.com/terraform/install)
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- S3 bucket `hexagone-terraform-state` for remote state (create manually once)

## Getting Started

```bash
cd terraform/production
terraform init
terraform plan -var="lambda_image_tag=$(git rev-parse --short HEAD)"
terraform apply
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `domain_name` | `hexagone.one` | Domain for CloudFront and ACM certificate |
| `lambda_image_tag` | `latest` | Docker image tag for the backend Lambda function |

## Deploying the Backend

Build, push the Docker image to ECR, then update the Lambda function:

```bash
cd apps/backend

# 1. Get the ECR repository URL
ECR_URL=$(terraform -chdir=../../terraform/production output -raw ecr_repository_url)

# 2. Authenticate Docker with ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin "$ECR_URL"

# 3. Build the Lambda Docker image
docker build -f Dockerfile.lambda --platform linux/arm64 -t hexagone-backend:latest .

# 4. Tag and push
IMAGE_TAG=$(git rev-parse --short HEAD)
docker tag hexagone-backend:latest "$ECR_URL:$IMAGE_TAG"
docker push "$ECR_URL:$IMAGE_TAG"

# 5. Update the Lambda function to use the new image
aws lambda update-function-code \
  --function-name hexagone-backend \
  --image-uri "$ECR_URL:$IMAGE_TAG" \
  --region eu-west-1

# 6. Verify
curl https://hexagone.one/api/health
```

Alternatively, deploy via Terraform by setting the image tag variable:

```bash
cd terraform/production
terraform apply -var="lambda_image_tag=$IMAGE_TAG"
```

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
