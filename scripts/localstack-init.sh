#!/bin/bash
set -euo pipefail

REGION="eu-west-2"
BUCKET="hexagone-gpx-uploads"
FUNCTION_NAME="hexagone-gpx-processor"

awslocal s3 mb "s3://${BUCKET}" --region "${REGION}"

# Create shim Lambda that forwards S3 events to the compose service
cat > /tmp/shim.py << 'PYTHON'
import json
import urllib.request

LAMBDA_ENDPOINT = (
    "http://hexagone-lambda-file-upload:8080"
    "/2015-03-31/functions/function/invocations"
)

def handler(event, context):
    data = json.dumps(event).encode()
    req = urllib.request.Request(
        LAMBDA_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
PYTHON

cd /tmp && zip -q shim.zip shim.py

awslocal lambda create-function \
  --function-name "${FUNCTION_NAME}" \
  --runtime python3.12 \
  --handler shim.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --zip-file fileb:///tmp/shim.zip \
  --region "${REGION}" \
  --timeout 30

awslocal lambda wait function-active-v2 \
  --function-name "${FUNCTION_NAME}" \
  --region "${REGION}"

awslocal lambda add-permission \
  --function-name "${FUNCTION_NAME}" \
  --statement-id s3-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${BUCKET}" \
  --region "${REGION}"

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
