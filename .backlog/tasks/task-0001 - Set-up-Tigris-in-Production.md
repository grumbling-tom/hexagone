---
id: TASK-0001
title: Set up Tigris in Production
status: In Progress
assignee: []
created_date: '2026-06-16 10:45'
updated_date: '2026-06-17 11:02'
labels: []
milestone: m-1
dependencies: []
references:
  - 'https://github.com/grumbling-tom/hexagone/pull/55'
  - infra/terraform/storage.tf
  - infra/terraform/main.tf
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provision the production GPX object storage on Tigris so the deployed app can store uploads. The backend was already wired to Tigris (endpoint, region, bucket name, and presigned-URL credentials via the `hexagone-backend-secrets` Secret), but the bucket itself was never created in production — uploads failed with `NoSuchBucket`. This task creates the bucket and its CORS policy as managed infrastructure.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The hexagone-gpx-uploads bucket is created in Tigris via Terraform (not by hand)
- [ ] #2 The bucket has a CORS policy allowing GET/PUT from the production app origin (the Cloudflare apex), mirroring scripts/seaweedfs-init.sh for local dev
- [x] #3 The Terraform bucket name stays in sync with HEXAGONE_S3_BUCKET in infra/k8s/base/app/backend.yaml
- [ ] #4 Uploads work end-to-end in the deployed app: presigned PUT and GET succeed from the browser
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Manage the bucket in the existing Cloudflare Terraform root (infra/terraform/), since Tigris is S3-compatible:

- Add an `aws` provider pointed at the Tigris endpoint (https://t3.storage.dev, path-style, AWS preflight skipped), reusing the same AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env credentials as the Tigris state backend.
- New infra/terraform/storage.tf: `aws_s3_bucket.uploads` + `aws_s3_bucket_cors_configuration.uploads` (GET/PUT from https://${local.app_hostname}, reusing the apex from cloudflare.tf).
- `terraform apply` (run as part of scripts/prod-stack.sh up) creates the bucket; if it was pre-created by hand, import with `terraform import aws_s3_bucket.uploads hexagone-gpx-uploads` first.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause of the production upload failure: only the Terraform *state* bucket (hexagone-tfstate) had been bootstrapped; the *uploads* bucket (hexagone-gpx-uploads) was never created, so presigned PUTs returned NoSuchBucket.

Considered the native tigrisdata/tigris provider (cleaner bucket resource, reuses AWS_* env creds), but it has no CORS resource (resources: bucket, bucket_fork, bucket_public_access, bucket_shadow_config, bucket_snapshot, bucket_website_config). Since the browser PUTs directly to Tigris via presigned URLs, CORS is required — so we use the aws provider for both bucket and CORS rather than splitting across two providers.

Validated with `terraform validate` (config valid, both providers resolve). The provider lock is gitignored, so the script's `terraform init` regenerates it on the mini.

Not yet verified end-to-end against the live deployment — needs a `terraform apply` on the mini and a real upload to confirm the presigned PUT/GET round-trip and CORS.
<!-- SECTION:NOTES:END -->
