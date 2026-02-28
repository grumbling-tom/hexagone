#!/usr/bin/env bash
# Assume the HexagoneInfrastructureAdmin to get temporary AWS credentials
#
# This script uses the hexagone-local-dev IAM user credentials to assume
# the HexagoneInfrastructureAdmin, which provides the same AWS permissions
# as the CI/CD pipeline. The temporary credentials expire after 12 hours.
#
# Usage:
#   # Source the script to set environment variables in your current shell
#   AWS_PROFILE=hexagone-local-dev AWS_ACCOUNT_ID=... source scripts/assume-role.sh
#
#   # Or eval the output
#   eval $(AWS_PROFILE=hexagone-local-dev AWS_ACCOUNT_ID=... scripts/assume-role.sh)

set -euo pipefail

# Configuration
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/HexagoneInfrastructureAdmin"
SESSION_NAME="local-terraform-$(date +%Y%m%d-%H%M%S)"
DURATION_SECONDS=43200  # 12 hours

# Assume the role
CREDENTIALS=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --duration-seconds "$DURATION_SECONDS" \
  --output json)

# Check if the assume-role command succeeded
if [ $? -ne 0 ]; then
  echo "Error: Failed to assume role"
  echo "$CREDENTIALS"
  echo ""
  echo "Possible causes:"
  echo "1. IAM user credentials not configured (check ~/.aws/credentials or AWS_* env vars)"
  echo "2. HexagoneInfrastructureAdmin trust policy doesn't allow the IAM user to assume it"
  echo "3. IAM user doesn't have sts:AssumeRole permission for this role"
  exit 1
fi

# Parse the credentials from the JSON response
ACCESS_KEY_ID=$(echo "$CREDENTIALS" | yq -r '.Credentials.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$CREDENTIALS" | yq -r '.Credentials.SecretAccessKey')
SESSION_TOKEN=$(echo "$CREDENTIALS" | yq -r '.Credentials.SessionToken')
EXPIRATION=$(echo "$CREDENTIALS" | yq -r '.Credentials.Expiration')

# Validate that we got credentials
if [ -z "$ACCESS_KEY_ID" ] || [ "$ACCESS_KEY_ID" = "null" ]; then
  echo "Error: Failed to parse credentials from assume-role response"
  exit 1
fi

# Output export statements
echo "export AWS_ACCESS_KEY_ID='$ACCESS_KEY_ID'"
echo "export AWS_SECRET_ACCESS_KEY='$SECRET_ACCESS_KEY'"
echo "export AWS_SESSION_TOKEN='$SESSION_TOKEN'"
echo "export AWS_REGION=eu-west-1"
echo "# Credentials expire at: $EXPIRATION" >&2
echo "# Session: $SESSION_NAME" >&2
