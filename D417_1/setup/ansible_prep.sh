#!/bin/bash

ansible-vault encrypt vault.yaml

ansible-playbook -i hosts.yaml create_user.yaml --ask-vault=pass