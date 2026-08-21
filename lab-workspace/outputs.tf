output "aws_account_id" {
  description = "Verified AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "lab_vpc_id" {
  description = "The dynamically discovered cloudacademylabs VPC ID"
  value       = data.aws_vpc.lab_vpc.id
}

output "ubuntu_server_ip" {
  description = "Public IP address for the Ubuntu 24.04 node"
  value       = aws_instance.ubuntu_server.public_ip
}

output "rhel_server_ip" {
  description = "Public IP address for the RHEL 10 node"
  value       = aws_instance.rhel_server.public_ip
}