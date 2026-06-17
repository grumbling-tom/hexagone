# Tigris bucket for GPX uploads. The browser uploads directly to this bucket via
# backend-issued presigned PUT URLs (and reads via presigned GET), so it needs a
# CORS policy for the app origin — the prod analogue of the local SeaweedFS setup
# in scripts/seaweedfs-init.sh. Managed with the aws provider (configured for the
# Tigris endpoint in main.tf), since Tigris is S3-compatible.

locals {
  # Must match HEXAGONE_S3_BUCKET in infra/k8s/base/app/backend.yaml.
  uploads_bucket = "hexagone-gpx-uploads"
  # Must match BACKUP_BUCKET in infra/k8s/base/app/db-backup.yaml + scripts/prod-stack.sh.
  db_backups_bucket = "hexagone-db-backups"
}

resource "aws_s3_bucket" "uploads" {
  bucket = local.uploads_bucket
}

# CORS for the browser's direct presigned PUT/GET. Mirrors seaweedfs-init.sh, but
# the allowed origin is the public apex (local.app_hostname, from cloudflare.tf)
# instead of the localhost dev origins.
resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_origins = ["https://${local.app_hostname}"]
    allowed_methods = ["GET", "PUT"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "Content-Disposition"]
    max_age_seconds = 3000
  }
}

# Dedicated bucket for Postgres logical-dump backups (the pg_dump CronJob in
# infra/k8s/base/app/db-backup.yaml writes here; prod-stack.sh backup/restore
# read/write it). Server-side only, so no CORS.
resource "aws_s3_bucket" "db_backups" {
  bucket = local.db_backups_bucket
}

# NOTE: the bucket's 7-day expiry lifecycle rule is deliberately NOT managed here.
# The aws provider's `aws_s3_bucket_lifecycle_configuration` does a post-write
# read-back "stabilization" wait that times out against Tigris (and other
# S3-compatible stores) even though the PUT succeeds — see
# https://github.com/hashicorp/terraform-provider-aws/issues/25939. So apply
# always errored despite the rule being correctly applied. Instead, scripts/
# prod-stack.sh sets it with an idempotent `aws s3api put-bucket-lifecycle-
# configuration` (a plain PUT, no read-back loop). Keep the rule definition there
# in sync with the 7-day retention intent.
