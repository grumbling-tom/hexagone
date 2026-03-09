#!/usr/bin/env bash
# Export DBT_* environment variables from Terraform outputs.
#
# Usage:
#   eval $(bash scripts/dbt-env.sh)

set -euo pipefail

TERRAFORM_DIR="terraform/production"

echo "export DBT_HOST=$(terraform -chdir="$TERRAFORM_DIR" output -raw database_host)"
echo "export DBT_PORT=$(terraform -chdir="$TERRAFORM_DIR" output -raw database_port)"
echo "export DBT_USER=$(terraform -chdir="$TERRAFORM_DIR" output -raw database_user)"
echo "export DBT_PASSWORD=$(terraform -chdir="$TERRAFORM_DIR" output -raw db_password)"
echo "export DBT_DBNAME=$(terraform -chdir="$TERRAFORM_DIR" output -raw database_name)"