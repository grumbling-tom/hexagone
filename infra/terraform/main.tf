terraform {
  required_version = ">= 1.10.0" # use_lockfile (S3-native state locking) needs 1.10+

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
    # Tigris is S3-compatible, so its object-storage buckets are managed with the
    # aws provider pointed at the Tigris endpoint (see the provider block below).
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # State lives in Tigris (https://t3.storage.dev) — S3-compatible, no egress
  # fees. Tigris supports If-None-Match conditional writes, so use_lockfile gives
  # real state locking without DynamoDB.
  #
  # The backend block can't use variables, so Tigris credentials come from env:
  #   export AWS_ACCESS_KEY_ID=tid_...        # Tigris access key
  #   export AWS_SECRET_ACCESS_KEY=tsec_...   # Tigris secret
  #
  # The aws provider below reuses these same env credentials to manage Tigris
  # buckets — it targets the Tigris endpoint, not an AWS account, so there's no
  # real AWS in play (this stack lives apart from the legacy terraform/ dir).
  #
  # Bootstrap the bucket once (the backend won't create it):
  #   aws s3 mb s3://hexagone-tfstate --endpoint-url https://t3.storage.dev
  backend "s3" {
    bucket = "hexagone-tfstate"
    key    = "infra/terraform.tfstate"
    region = "auto"

    endpoints = { s3 = "https://t3.storage.dev" }

    # Tigris is S3-compatible but not AWS — skip the AWS-specific preflight.
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true # remove only if Tigris accepts default checksums

    use_lockfile = true # conditional-write lock object; no DynamoDB
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Tigris object storage (S3-compatible). Points at the Tigris endpoint and reuses
# the AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env credentials used by the state
# backend above; no AWS account is involved, so the AWS-specific preflight checks
# are skipped (mirroring the backend block).
provider "aws" {
  region = "auto"

  skip_credentials_validation = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  s3_use_path_style = true # path-style addressing against the custom endpoint

  endpoints {
    s3 = "https://t3.storage.dev"
  }
}
