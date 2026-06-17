# Tigris bucket for GPX uploads. The browser uploads directly to this bucket via
# backend-issued presigned PUT URLs (and reads via presigned GET), so it needs a
# CORS policy for the app origin — the prod analogue of the local SeaweedFS setup
# in scripts/seaweedfs-init.sh. Managed with the aws provider (configured for the
# Tigris endpoint in main.tf), since Tigris is S3-compatible.

locals {
  # Must match HEXAGONE_S3_BUCKET in infra/k8s/base/app/backend.yaml.
  uploads_bucket = "hexagone-gpx-uploads"
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
