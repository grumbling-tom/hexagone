#!/usr/bin/env bash
# Assume the GitHubActionsDeployRole to get temporary AWS credentials
#
# This script uses the ClankLocalDevelopment IAM user credentials to assume
# the GitHubActionsDeployRole, which provides the same AWS permissions as
# the CI/CD pipeline. The temporary credentials expire after 12 hours.
#
# Prerequisites:
# 1. Configure ClankLocalDevelopment IAM user credentials in ~/.aws/credentials
#    or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
# 2. Update the GitHubActionsDeployRole trust policy to allow the IAM user to assume it
#
# Usage:
#   # Source the script to set environment variables in your current shell
#   source scripts/assume-role.sh
#
#   # Or eval the output
#   eval $(scripts/assume-role.sh)
#
#   # Or save to a file and source it
#   scripts/assume-role.sh > /tmp/aws-creds.sh && source /tmp/aws-creds.sh

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
  echo "2. GitHubActionsDeployRole trust policy doesn't allow the IAM user to assume it"
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
