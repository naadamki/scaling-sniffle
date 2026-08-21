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

data "aws_ami" "ubuntu_24_04" {
  most_recent = true
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical's official AWS account ID
}

data "aws_ami" "rhel_10" {
  most_recent = true
  owners      = ["309956199498"] # Red Hat's official AWS account ID

  filter {
    name   = "name"
    values = ["RHEL-10*_HVM-*-x86_64-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
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
  ami                         = data.aws_ami.ubuntu_24_04.id  
  instance_type               = var.instance_type
  key_name                    = var.ssh_key_name
  vpc_security_group_ids      = [aws_security_group.ssh_allow.id]
  subnet_id                   = data.aws_subnets.lab_subnets.ids[0]
  associate_public_ip_address = true

  tags = {
    Name = "Ubuntu-Server"
  }
}

# RHEL Node
resource "aws_instance" "rhel_server" {
  ami                         = data.aws_ami.rhel_10.id
  instance_type               = var.instance_type
  key_name                    = var.ssh_key_name
  vpc_security_group_ids      = [aws_security_group.ssh_allow.id]
  subnet_id                   = data.aws_subnets.lab_subnets.ids[0]
  associate_public_ip_address = true

  tags = {
    Name = "RHEL-Server"
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