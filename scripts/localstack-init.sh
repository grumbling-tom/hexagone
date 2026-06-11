#!/bin/bash
set -euo pipefail

# Create the GPX uploads bucket in the local S3 (localstack). The backend
# generates presigned PUT/GET URLs against this bucket. Processing of
# uploaded files is no longer wired up locally (the S3-triggered file-upload
# lambda was removed with the move to persistent services).
REGION="eu-west-2"
BUCKET="hexagone-gpx-uploads"

awslocal s3 mb "s3://${BUCKET}" --region "${REGION}"
