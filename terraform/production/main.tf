terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "hexagone-terraform-state"
    key    = "production/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = "eu-west-1"
}

# CloudFront requires ACM certificates in us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
