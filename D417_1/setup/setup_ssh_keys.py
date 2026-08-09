import os
import sys
import subprocess
import yaml
import pexpect
from netmiko import ConnectHandler

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, "N-CoreA-01.yaml")
CLOSET = "Access_Closet_1"

ENV_USER = os.environ.get("EXOS_DEFAULT_USER", "admin")
ENV_PASS = os.environ.get("EXOS_DEFAULT_PASS", "")  # Blank password
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa.pub")

def ensure_local_ssh_key():
    """Ensure RSA key pair exists on the Ansible master node."""
    private_key = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(private_key):
        print("[*] Generating new RSA SSH key pair (no passphrase)...")
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-m", "PEM", "-N", "", "-f", private_key],
            check=True
        )
    else:
        print("[+] Existing local SSH key pair found.")

def load_switches(file_path, closet_name):
    """Load switch list from YAML inventory."""
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"!! Failed to load inventory '{file_path}': {e}")
        sys.exit(1)

def scp_transfer_pexpect(ip, username, local_file, remote_filename="id_rsa.ssh"):
    """
    Uses pexpect to run system SCP with legacy ssh-rsa flags
    and automatically presses Enter for a blank password prompt.
    """
    scp_cmd = (
        f"scp -o HostKeyAlgorithms=+ssh-rsa "
        f"-o PubkeyAcceptedKeyTypes=+ssh-rsa "
        f"-o StrictHostKeyChecking=no "
        f"-o UserKnownHostsFile=/dev/null "
        f"{local_file} {username}@{ip}:{remote_filename}"
    )

    child = pexpect.spawn(scp_cmd, encoding='utf-8', timeout=15)
    
    # Wait for either the password prompt, key confirmation, or process termination
    index = child.expect([r'(?i)password:', r'Are you sure you want to continue', pexpect.EOF, pexpect.TIMEOUT])
    
    if index == 1:
        # Accept SSH host key prompt if requested
        child.sendline("yes")
        index = child.expect([r'(?i)password:', pexpect.EOF, pexpect.TIMEOUT])

    if index == 0:
        # Password prompt detected -> Send Enter for blank password
        child.sendline("")
        child.expect(pexpect.EOF)
        return True
    elif index == 2:
        # Process completed without prompt
        return True
    else:
        print(f"    [!] SCP timed out or failed. Output: {child.before}")
        return False

def main():
    ensure_local_ssh_key()
    switches = load_switches(INVENTORY_FILE, CLOSET)

    print("\nStarting Automated SSH Key Pairing via pexpect...\n")

    for sw in switches:
        ip = sw.get("host") if isinstance(sw, dict) else str(sw)
        sw_name = sw.get("hostname", ip) if isinstance(sw, dict) else ip

        print(f"----------------------------------------")
        print(f"Processing Switch: {sw_name} ({ip})")
        print(f"----------------------------------------")

        device = {
            'device_type': 'extreme_exos',
            'host': ip,
            'username': ENV_USER,
            'password': ENV_PASS,
            'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        }

        try:
            # 1. Connect via Netmiko and enable SSH2
            print("  [1/4] Enabling SSH2 on switch...")
            net = ConnectHandler(**device)
            net.send_command("enable ssh2")

            # 2. Use pexpect to SCP the public key
            print("  [2/4] Executing SCP transfer (pexpect handling blank pass)...")
            scp_success = scp_transfer_pexpect(ip, ENV_USER, SSH_KEY_PATH, "id_rsa.ssh")
            
            if not scp_success:
                print(f"  [!] Skipping key binding on {sw_name} due to SCP failure.")
                net.disconnect()
                continue

            print("  [+] SCP file transfer complete.")

            # 3. Bind the SSH key on EXOS
            print("  [3/4] Binding key 'id_rsa.ssh' to user 'admin'...")
            net.send_command("configure sshd2 user-key id_rsa.ssh add user admin")

            # 4. Save configuration
            save_out = net.send_command("save configuration primary", expect_string=r"(?i)y/n|\?")
            if "y/n" in save_out.lower() or "?" in save_out:
                net.send_command("y")

            net.disconnect()
            print("  [+] Switch configuration saved.")

        except Exception as e:
            print(f"  [!] Configuration failed on {sw_name}: {e}")
            continue

        # 5. Verify Passwordless SSH Connection
        print("  [4/4] Verifying passwordless SSH connection...")
        test_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "HostKeyAlgorithms=+ssh-rsa",
            "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            f"{ENV_USER}@{ip}",
            "show version"
        ]

        res = subprocess.run(test_cmd, capture_output=True, text=True)

        if res.returncode == 0:
            print(f"  [SUCCESS] Passwordless SSH verified for {sw_name}!\n")
        else:
            print(f"  [!] Verification failed for {sw_name}:\n{res.stderr.strip()}\n")

if __name__ == "__main__":
    main()