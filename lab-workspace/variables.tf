
variable "ssh_key_name" {
  type = string
}


# AWS Region Variable
variable "aws_region"{
description ="AWS Region"
#type = "string"
default ="us-west-2"
}

# EC2 Instance Type Variable
variable "instance_type"{
 description ="EC2 Instance type"
 #type ="string"
 default = "t2.micro"
}

# EC2 Key Pair Public Key Path Variable for SSH Access
variable "pubkey_path"{
 description = "EC2 key pair path for public key"
 #type ="string"
 default ="~/.ssh/your_key_name.pub"
}