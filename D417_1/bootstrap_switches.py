import os
import sys
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

def main():
    switches = load_switches(INVENTORY_FILE, CLOSET)
    print("\nStarting Fast Switch Bootstrapping...")

    for sw in switches:
        ip = sw.get("host") if isinstance(sw, dict) else str(sw)
        sw_name = sw.get("hostname", ip) if isinstance(sw, dict) else ip

        print(f"\n[*] Bootstrapping {sw_name} ({ip})...")

        device = {
            'device_type': 'extreme_exos',
            'host': ip,
            'username': ENV_USER,
            'password': ENV_PASS,
            'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        }

        try:
            net = ConnectHandler(**device)

            # 1. Start password change, wait for "Current user's password:"
            net.send_command("configure account admin password", expect_string=r"(?i)current user's password:")

            # 2. Press Enter for the current blank password, wait for "New password:"
            net.send_command("\n", expect_string=r"(?i)new password:")

            # 3. Type 1234, wait for "Reenter password:"
            net.send_command(NEW_ADMIN_PASS, expect_string=r"(?i)reenter password:")

            # 4. Re-type 1234 to confirm, wait for CLI prompt (#)
            net.send_command(NEW_ADMIN_PASS, expect_string=r"#")

            # 5. Enable SSH2
            net.send_command("enable ssh2")

            # 6. Save configuration
            save_out = net.send_command("save configuration primary", expect_string=r"(?i)y/n|\?")
            net.send_command("y", expect_string=r"#")

            net.disconnect()
            print(f"[+] Successfully set admin password to '{NEW_ADMIN_PASS}' on {sw_name}!")

        except Exception as e:
            print(f"[!] Failed to bootstrap {sw_name}: {e}")


if __name__ == "__main__":
    main()