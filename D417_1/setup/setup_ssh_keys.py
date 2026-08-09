import os
import subprocess
import sys
import yaml
import paramiko
from netmiko import ConnectHandler

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "..", "N-CoreA-01.yaml")
CLOSET = "Access_Closet_1"
EXOS_USER = "admin"
EXOS_PASS = ""  # Current blank password
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

def ensure_local_ssh_key():
    """Generate SSH key pair on Ansible Master if it doesn't exist."""
    private_key = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(private_key):
        print("[*] Generating new RSA SSH key pair (no passphrase)...")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-m", "PEM", "-N", "", "-f", private_key],
            check=True
        )
    else:
        print("[+] Existing SSH key pair found.")

def load_switches(file_path, closet_name):
    """Load switch list from YAML inventory."""
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"!! Failed to load inventory: {e}")
        sys.exit(1)

def transfer_key_via_paramiko(ip, username, password, local_file, remote_file):
    """Transfers public key file using Python Paramiko SFTP client."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh.connect(
        hostname=ip,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        disabled_algorithms={'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']}
    )
    
    sftp = ssh.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()
    ssh.close()

def main():
    ensure_local_ssh_key()
    switches = load_switches(INVENTORY_FILE, CLOSET)

    print("\nStarting Automated SSH Key Deployment & Verification...\n")

    for sw in switches:
        # Resolve IP directly from 'hostname' key
        if isinstance(sw, dict):
            ip = sw.get("hostname")
            sw_name = sw.get("name", ip)
        else:
            ip = str(sw)
            sw_name = str(sw)

        if not ip:
            print(f"[!] Could not determine IP address for entry: {sw}")
            continue

        print(f"----------------------------------------")
        print(f"Processing Switch: {sw_name} ({ip})")
        print(f"----------------------------------------")

        # Step 1: SFTP Transfer
        try:
            print(f"  [1/4] Transferring id_rsa.pub to {ip} via SFTP...")
            transfer_key_via_paramiko(ip, EXOS_USER, EXOS_PASS, SSH_KEY_PATH, "id_rsa.ssh")
            print("  [+] Transfer successful.")
        except Exception as e:
            print(f"  [!] SFTP Transfer failed on {ip}: {e}")

        # Step 2: Netmiko Configuration
        device = {
            'device_type': 'extreme_exos',
            'host': ip,
            'username': EXOS_USER,
            'password': EXOS_PASS,
            'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        }

        try:
            print("  [2/4] Enabling SSH2 and binding SSH key on switch...")
            net = ConnectHandler(**device)
            
            # EXOS Commands
            net.send_command_timing("enable ssh2")
            net.send_command_timing("configure sshd2 user-key id_rsa.ssh add user admin")

            save_out = net.send_command_timing("save configuration primary")
            if "y/N" in save_out or "?" in save_out or "y/n" in save_out.lower():
                net.send_command_timing("y")
            else:
                net.send_command_timing("save configuration")

            net.disconnect()
            print("  [3/4] Switch configuration saved.")

        except Exception as e:
            print(f"  [!] Failed CLI configuration on {ip}: {e}")
            continue

        # Step 3: Passwordless SSH Verification
        print("  [4/4] Verifying passwordless SSH access from Ansible Master...")
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
            print(f"  [SUCCESS] Passwordless SSH verified for {ip}!")
        else:
            print(f"  [!] Verification failed for {ip}:\n{res.stderr.strip()}")

if __name__ == "__main__":
    main()