#!/bin/bash

ansible-galaxy collection install community.network

ansible-vault encrypt vault.yaml

ansible-playbook -i hosts.yaml create_user.yaml --ask-vault=pass