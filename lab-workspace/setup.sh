#!/bin/bash


export TF_VAR_ssh_key_name=$(aws ec2 describe-key-pairs --query "KeyPairs[0].KeyName" --output text)

