#!/bin/sh
set -eu

# Create the GPX uploads bucket in the local S3 (SeaweedFS) and apply the CORS
# policy the browser needs to upload directly via presigned PUT URLs. The
# backend generates presigned PUT/GET URLs against this bucket. Processing of
# uploaded files is no longer wired up locally (the S3-triggered file-upload
# lambda was removed with the move to persistent services).
#
# Unlike LocalStack, SeaweedFS has no env-var CORS knob, so CORS is set at
# runtime via the S3 PutBucketCors API. Credentials come from the env vars
# below, which match the admin identity SeaweedFS derives from
# AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY (see docker-compose.yml).
ENDPOINT="http://seaweedfs:4566"
BUCKET="hexagone-gpx-uploads"

# The S3 gateway comes up a beat after the master's healthcheck passes; retry
# a cheap ListBuckets until it answers before issuing real operations.
echo "Waiting for SeaweedFS S3 at ${ENDPOINT}..."
i=0
until aws --endpoint-url "$ENDPOINT" s3 ls >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 30 ]; then
    echo "SeaweedFS S3 did not become ready in time" >&2
    exit 1
  fi
  sleep 1
done

# Idempotent: re-running compose must not fail if the bucket already exists.
aws --endpoint-url "$ENDPOINT" s3 mb "s3://${BUCKET}" 2>/dev/null || true

# Allow-list both browser origins that PUT directly to S3: the bare dev server
# (http://localhost:3000) and the portless HTTPS URL (https://hexagone.localhost,
# see apps/web `pnpm dev:https`). http://localhost:4566 is a secure context for
# the HTTPS page, so the cross-origin PUT needs no proxying — only this CORS rule.
aws --endpoint-url "$ENDPOINT" s3api put-bucket-cors \
  --bucket "$BUCKET" \
  --cors-configuration '{
    "CORSRules": [
      {
        "AllowedOrigins": ["http://localhost:3000", "https://hexagone.localhost"],
        "AllowedMethods": ["GET", "PUT"],
        "AllowedHeaders": ["*"],
        "ExposeHeaders": ["ETag", "Content-Disposition"],
        "MaxAgeSeconds": 3000
      }
    ]
  }'

echo "SeaweedFS ready: bucket ${BUCKET} created with CORS for localhost:3000 + hexagone.localhost"
