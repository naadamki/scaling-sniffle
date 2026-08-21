terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

# Query the pre-existing 'cloudacademylabs' VPC
data "aws_vpc" "lab_vpc" {
  filter {
    name   = "tag:Name"
    values = ["cloudacademylabs"]
  }
}

# Subnet ID retrieval from that VPC
data "aws_subnets" "lab_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.lab_vpc.id]
  }
}

# Security Group for Ansible SSH
resource "aws_security_group" "ssh_allow" {
  name        = "allow_ssh_cloudacademy"
  description = "Allow SSH inbound traffic for Ansible"
  vpc_id      = data.aws_vpc.lab_vpc.id

  ingress {
    description      = "SSH"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Ubuntu Node
resource "aws_instance" "ubuntu_server" {
  ami                         = "ami-0360c520857e3138f"
  instance_type               = "t2.micro"
  key_name                    = var.ssh_key_name
  vpc_security_group_ids      = [aws_security_group.ssh_allow.id]
  subnet_id                   = data.aws_subnets.lab_subnets.ids[0]
  associate_public_ip_address = true

  tags = {
    Name = "Ubuntu-Lab-Node"
  }
}

# RHEL Node
resource "aws_instance" "rhel_server" {
  ami                         = "ami-0fd3ac4abb734302a"
  instance_type               = "t2.micro"
  key_name                    = var.ssh_key_name
  vpc_security_group_ids      = [aws_security_group.ssh_allow.id]
  subnet_id                   = data.aws_subnets.lab_subnets.ids[0]
  associate_public_ip_address = true

  tags = {
    Name = "RHEL-Lab-Node"
  }
}

# Automatic Ansible inventory creator - pulls public_ips for use in Ansible script
resource "local_file" "ansible_inventory" {
  content  = <<-EOT
    [ubuntu_nodes]
    ${aws_instance.ubuntu_server.public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=${var.ssh_key_name}.pem

    [rhel_nodes]
    ${aws_instance.rhel_server.public_ip} ansible_user=ec2-user ansible_ssh_private_key_file=${var.ssh_key_name}.pem

    [all:vars]
    ansible_python_interpreter=/usr/bin/python3
  EOT
  filename = "${path.module}/inventory.ini"
}