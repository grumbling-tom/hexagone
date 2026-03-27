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

# Public subnets for fck-nat and Internet Gateway access
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

# fck-nat gives Lambda (in private subnets) outbound internet access
# without exposing it to inbound traffic from the internet.
# Uses a t4g.nano EC2 instance (~$3/mo) instead of managed NAT Gateway (~$39/mo).
# Traffic flow: Lambda → fck-nat instance (public subnet) → Internet Gateway → Internet
# Auto-recovery: ASG (min=max=1) replaces the instance on failure.

data "aws_ami" "fck_nat" {
  most_recent = true
  owners      = ["568608671756"]

  filter {
    name   = "name"
    values = ["fck-nat-al2023-*-arm64-*"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_security_group" "fck_nat" {
  name        = "hexagone-fck-nat-sg"
  description = "Security group for fck-nat NAT instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [for s in aws_subnet.private : s.cidr_block]
    description = "Allow all traffic from private subnets"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}

resource "aws_network_interface" "fck_nat" {
  subnet_id         = aws_subnet.public[0].id
  security_groups   = [aws_security_group.fck_nat.id]
  source_dest_check = false
  description       = "Stable ENI for fck-nat instance, persists across ASG replacements"
}

resource "aws_launch_template" "fck_nat" {
  name_prefix   = "hexagone-fck-nat-"
  image_id      = data.aws_ami.fck_nat.id
  instance_type = "t4g.micro"

  network_interfaces {
    network_interface_id = aws_network_interface.fck_nat.id
    device_index         = 0
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "hexagone-fck-nat"
    }
  }
}

resource "aws_autoscaling_group" "fck_nat" {
  name_prefix      = "hexagone-fck-nat-"
  min_size         = 1
  max_size         = 1
  desired_capacity = 1

  availability_zones = [data.aws_availability_zones.available.names[0]]

  launch_template {
    id      = aws_launch_template.fck_nat.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "hexagone-fck-nat"
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
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
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_network_interface.fck_nat.id
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
