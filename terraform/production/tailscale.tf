# Tailscale Subnet Router
# A small EC2 instance that acts as a Tailscale subnet router, allowing
# developers on the Tailscale network to reach the private RDS instance.
#
# --- Rotation (every ~60 days, before the 90-day auth key expires) ---
#
# 1. Generate a new auth key at https://login.tailscale.com/admin/settings/keys
#    (reusable, ephemeral, with subnet router tag)
# 2. Taint the instance and apply with the new key:
#      terraform -chdir=terraform/production taint aws_instance.tailscale
#      terraform -chdir=terraform/production apply -var="tailscale_auth_key=tskey-auth-..."
# 3. Approve the subnet routes for the new node in the Tailscale admin console:
#      https://login.tailscale.com/admin/machines
# 4. Remove the old (offline) node from the Tailscale admin console
# 5. Verify connectivity: nc -zv <rds-endpoint> 5432

data "aws_ssm_parameter" "al2023_x86_64" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_security_group" "tailscale" {
  name        = "hexagone-tailscale-sg"
  description = "Security group for Tailscale subnet router"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}

resource "aws_iam_role" "tailscale" {
  name = "HexagoneTailscaleRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "tailscale_ssm" {
  role       = aws_iam_role.tailscale.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "tailscale" {
  name = "HexagoneTailscaleProfile"
  role = aws_iam_role.tailscale.name
}

resource "aws_instance" "tailscale" {
  ami                    = data.aws_ssm_parameter.al2023_x86_64.value
  instance_type          = "t3.small"
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.tailscale.id]
  iam_instance_profile   = aws_iam_instance_profile.tailscale.name

  # Required for subnet routing — the instance forwards packets
  # destined for private subnet CIDRs, not for itself.
  source_dest_check = false

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -euo pipefail

    # By default Linux drops packets not addressed to it. Since this instance
    # is a router (forwarding packets from Tailscale to the private subnets),
    # we must enable IP forwarding at the OS level. This is the counterpart to
    # source_dest_check = false which does the same at the AWS level.
    echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.d/99-tailscale.conf
    echo 'net.ipv6.conf.all.forwarding = 1' >> /etc/sysctl.d/99-tailscale.conf
    sysctl -p /etc/sysctl.d/99-tailscale.conf

    # Install Tailscale
    dnf install -y dnf-plugins-core
    dnf config-manager --add-repo https://pkgs.tailscale.com/stable/amazon-linux/2023/tailscale.repo
    dnf install -y tailscale

    # Enable and start tailscaled
    systemctl enable --now tailscaled

    # Authenticate and advertise private subnet routes
    tailscale up \
      --authkey=${var.tailscale_auth_key} \
      --advertise-routes=${join(",", aws_subnet.private[*].cidr_block)} \
      --accept-dns=false \
      --hostname=hexagone-subnet-router
  EOF
  )

  tags = {
    Name = "hexagone-tailscale-router"
  }

  lifecycle {
    create_before_destroy = true
  }
}
