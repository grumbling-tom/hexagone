data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

# Public subnets for NAT Gateway
# Using /19 CIDR blocks to efficiently utilize the VPC IP range
# 3 public subnets: 10.0.0.0/19, 10.0.32.0/19, 10.0.64.0/19
resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index * 32}.0/19"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

# Private subnets for RDS and Lambda
# Using /19 CIDR blocks to efficiently utilize the VPC IP range
# 3 private subnets: 10.0.96.0/19, 10.0.128.0/19, 10.0.160.0/19
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${(count.index + 3) * 32}.0/19"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# NAT Gateway gives Lambda (in private subnets) outbound internet access
# without exposing it to inbound traffic from the internet.
# Traffic flow: Lambda → NAT Gateway (public subnet) → Internet Gateway → Internet
#
# To restrict outbound traffic to specific domains, add an AWS Network Firewall
# between the private subnets and the NAT Gateway. Example:
#
#   resource "aws_networkfirewall_firewall" "main" {
#     name                = "clank-firewall"
#     firewall_policy_arn = aws_networkfirewall_firewall_policy.main.arn
#     vpc_id              = aws_vpc.main.id
#     subnet_mapping { subnet_id = aws_subnet.firewall[0].id }
#   }
#
#   resource "aws_networkfirewall_rule_group" "domain_allow" {
#     capacity = 100
#     name     = "clank-allowed-domains"
#     type     = "STATEFUL"
#     rule_group {
#       rules_source {
#         rules_source_list {
#           generated_rules_type = "ALLOWLIST"
#           target_types         = ["TLS_SNI", "HTTP_HOST"]
#           targets              = [".example.com"]
#         }
#       }
#     }
#   }
#
# This requires a dedicated firewall subnet tier and modified route tables so
# private subnet traffic routes through the firewall endpoints before reaching
# the NAT Gateway. See: https://docs.aws.amazon.com/network-firewall/latest/developerguide/arch-igw-ngw.html

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_route_table_association" "private" {
  count          = 3
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "lambda" {
  name        = "hexagone-lambda-sg"
  description = "Security group for Hexagone Lambda functions"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}

resource "aws_security_group" "rds" {
  name        = "hexagone-rds-sg"
  description = "Security group for Hexagone RDS instance"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "Allow PostgreSQL access from Lambda"
  }

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.tailscale.id]
    description     = "Allow PostgreSQL access from Tailscale subnet router"
  }

  egress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "Allow TCP outbound traffic to Lambda on all ports"
  }
}
