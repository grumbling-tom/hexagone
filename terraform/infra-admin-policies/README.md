# Infra Admin Managed Policies

These JSON files are the source of truth for the `HexagoneInfrastructureAdmin` IAM role's permissions. They are applied **manually** via the AWS console (not managed by Terraform).

## Policies

| Policy name                 | File                             | Scope                                     |
| --------------------------- | -------------------------------- | ----------------------------------------- |
| `HexagoneInfraAdminStorage` | `HexagoneInfraAdminStorage.json` | S3, CloudFront, ACM, Route 53             |
| `HexagoneInfraAdminCompute` | `HexagoneInfraAdminCompute.json` | Lambda, API Gateway, ECR, CloudWatch Logs |
| `HexagoneInfraAdminNetwork` | `HexagoneInfraAdminNetwork.json` | VPC, EC2, SSM                             |
| `HexagoneInfraAdminIAM`     | `HexagoneInfraAdminIAM.json`     | IAM roles/instance profiles, RDS          |

## How to apply

1. Open [IAM Policies](https://console.aws.amazon.com/iam/home#/policies) in the AWS console
2. For each JSON file:
   - Click **Create policy** (or find the existing policy and click **Edit**)
   - Switch to the **JSON** tab
   - Paste the contents of the file
   - Name the policy to match the filename (without `.json`)
   - Save
3. Go to [IAM Roles](https://console.aws.amazon.com/iam/home#/roles) and find `HexagoneInfrastructureAdmin`
4. Attach all four managed policies
5. Remove any old inline policies from the role

## Size limits

AWS managed policies have a 6,144-character limit per policy. A role can have up to 10 managed policies attached. We use 4 of 10 slots, leaving 6 free.
