#!/bin/bash

ansible-galaxy collection install -r requirements.yml


# 1. Ensure a local SSH key exists (generates one if it doesn't)
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "Generating local SSH key..."
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
fi

# Make sure sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass to handle blank passwords..."
    apt-get update && apt-get install -y sshpass
fi

# Array of your switch IP addresses
SWITCHES=("10.10.1.20" "10.10.1.21" "10.10.1.22" "10.10.1.23" "10.10.1.24")

for IP in "${SWITCHES[@]}"; do
    echo "========================================"
    echo "Configuring switch: $IP"
    echo "========================================"

    # 2. SCP the public key to the switch using sshpass with an empty password
    echo "--> Uploading public key via SCP..."
    sshpass -p "" scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAcceptedAlgorithms=+ssh-rsa -o HostKeyAlgorithms=+ssh-rsa \
        ~/.ssh/id_rsa.pub admin@$IP:id_rsa.pub

    # 3. SSH into the switch, enable ssh2, map the user-key, and save
    echo "--> Configuring SSH key and saving configuration..."
    sshpass -p "" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAcceptedAlgorithms=+ssh-rsa -o HostKeyAlgorithms=+ssh-rsa \
        admin@$IP << 'EOF'
enable ssh2
configure sshd2 user-key id_rsa.pub add user admin
save configuration primary
y
exit
EOF

    echo "--> Finished $IP successfully."
    echo ""
done

echo "All switches successfully configured for key-based SSH access!"