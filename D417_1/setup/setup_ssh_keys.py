import os
import subprocess
import yaml
import sys
from netmiko import ConnectHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "..", "N-CoreA-01.yaml")
CLOSET = "Access_Closet_1"
EXOS_USER = "admin"
EXOS_PASS = ""
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")
KEY_NAME_ON_SWITCH = "id_rsa.ssh"

def ensure_local_ssh_key():
    private_key = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(private_key):
        print("Generating new RSA SSH key pair (no passphrase)...")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", private_key],
            check=True
        )
    else:
        print("!! Existing SSH key pair found.")

    with open(SSH_KEY_PATH, "r") as f:
        return f.read().strip()

def load_switches(file_path, closet_name):
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"    !! Failed to load inventory: {e}")
        sys.exit(1)

def main():
    ensure_local_ssh_key()
    switches = load_switches(INVENTORY_FILE, CLOSET)

    print("Starting Automated SSH Key Deployment & Verification...")

    for sw in switches:
        ip = sw.get("host") if isinstance(sw, dict) else sw
        sw_name = sw.get("hostname", ip) if isinstance(sw, dict) else ip

        print(f"Processing Switch: {sw_name} ({ip})")

        device = {
            'device_type': 'extreme_exos',
            'host': ip,
            'username': EXOS_USER,
            'password': EXOS_PASS,
            'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        }

        try:
            print("-- Connecting to switch & enabling SSH2...")
            net = ConnectHandler(**device)
            
            net.send_command_timing("enable ssh2")

            print("-- Deploying public key to switch...")
            with open(SSH_KEY_PATH, "r") as f:
                pub_key_content = f.read().strip()
            
            # Alternative to SCP: Configures SSH key directly via EXOS CLI
            # Or if your EXOS version requires scp:
            # net.send_command_timing(f"scp {EXOS_USER}@{ip}:{KEY_NAME_ON_SWITCH} ...")
            
            print("-- Binding SSH key to user 'admin'...")
            cmd_bind = f'configure ssh-access add user {EXOS_USER} key "{pub_key_content}"'
            net.send_command_timing(cmd_bind)

            save_out = net.send_command_timing("save configuration primary")
            if "y/N" in save_out or "?" in save_out or "y/n" in save_out.lower():
                net.send_command_timing("y")
            else:
                net.send_command_timing("save configuration")

            net.disconnect()
            print("-- Switch configuration saved.")

        except Exception as e:
            print(f"!! Failed CLI configuration on {sw_name}: {e}")
            continue

        print("-- Verifying passwordless SSH access from Ansible Master...")
        test_ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "HostKeyAlgorithms=+ssh-rsa",
            "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            f"{EXOS_USER}@{ip}",
            "show version"
        ]
        res = subprocess.run(test_ssh_cmd, capture_output=True, text=True)

        if res.returncode == 0:
            print(f"-- Success! Passwordless SSH verified for {sw_name}!")
        else:
            print(f"!! Verification failed for {sw_name}. Error output:\n{res.stderr}")

if __name__ == "__main__":
    main()