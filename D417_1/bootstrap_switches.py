import os
import sys
import subprocess
import yaml
from netmiko import ConnectHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "N-CoreA-01.yaml")
CLOSET = "Access_Closet_1"

ENV_USER = os.environ.get("EXOS_DEFAULT_USER", "admin")
ENV_PASS = os.environ.get("EXOS_DEFAULT_PASS", "")
NEW_ADMIN_PASS = "1234"

def load_switches(file_path, closet_name):
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"!! Failed to load inventory '{file_path}': {e}")
        sys.exit(1)

def ensure_local_ssh_key():
    """Generate SSH key pair on Ansible Master if it doesn't exist."""
    private_key = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(private_key):
        print("Generating new RSA SSH key pair (no passphrase)...")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-m", "PEM", "-N", "", "-f", private_key],
            check=True
        )
    else:
        print(f"    !! Existing SSH key pair found.")

def main():
    switches = load_switches(INVENTORY_FILE, CLOSET)
    print("\nStarting EXOS SSH pairing...")

    for sw in switches:
        ip = sw.get("host") if isinstance(sw, dict) else str(sw)
        sw_name = sw.get("hostname", ip) if isinstance(sw, dict) else ip

        device = {
            'device_type': 'extreme_exos',
            'host': ip,
            'username': ENV_USER,
            'password': ENV_PASS,
            'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        }

        try:
            net = ConnectHandler(**device)
            net.send_command("enable ssh2")
            net.send_command("save configuration primary")
            print(f"    -- Enabled SSH2 on EXOS.")    
            net.disconnect()

        except Exception as e:
            print(f"    !! Failed to send command to {sw_name}: {e}")

        ensure_local_ssh_key()

        public_key = os.path.expanduser("~/.ssh/id_rsa.pub")

        remote_destination = f"{ENV_USER}@{ip}:id_rsa.ssh"

        command = ["scp", public_key, remote_destination]

        subprocess.run(command, check=True, text=True, capture_output=True)

        
        """
            When this was ran: "ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa admin@10.10.1.20", it worked. How can I (or do I need to) include those variables in an SCP send?
        """
            
        try:
            net = ConnectHandler(**device)
            net.send_command("configure sshd2 user-key id_rsa add user admin")
            net.send_command("save configuration primary")
            net.disconnect()

        except Exception as e:
            print(f"    !! Failed to connect to {sw_name}: {e}")



if __name__ == "__main__":
    main()







