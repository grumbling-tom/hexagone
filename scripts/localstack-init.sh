#!/bin/bash
set -euo pipefail

REGION="eu-west-2"
BUCKET="hexagone-gpx-uploads"
FUNCTION_NAME="hexagone-gpx-processor"

awslocal s3 mb "s3://${BUCKET}" --region "${REGION}"

awslocal lambda create-function \
  --function-name "${FUNCTION_NAME}" \
  --runtime python3.12 \
  --handler src.app.handlers.gpx.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --code '{"S3Bucket":"hot-reload","S3Key":"/opt/code/backend"}' \
  --region "${REGION}" \
  --timeout 30

awslocal s3api put-bucket-notification-configuration \
  --bucket "${BUCKET}" \
  --region "${REGION}" \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:'"${REGION}"':000000000000:function:'"${FUNCTION_NAME}"'",
        "Events": ["s3:ObjectCreated:*"]
      }
    ]
  }'
