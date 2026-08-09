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

            # 1. Trigger password change. Netmiko's trailing \n satisfies "Current user's password:",
            #    so EXOS jumps straight to "New password:"
            net.send_command("configure account admin password", expect_string=r"(?i)new password:")

            # 2. Send 1234, wait for "Reenter password:"
            net.send_command(NEW_ADMIN_PASS, expect_string=r"(?i)reenter password:")

            # 3. Confirm 1234, wait for CLI prompt (#)
            net.send_command(NEW_ADMIN_PASS, expect_string=r"#")

            # 4. Enable SSH2
            net.send_command("enable ssh2")

            # 5. Save configuration
            save_out = net.send_command("save configuration primary", expect_string=r"(?i)y/n|\?")
            net.send_command("y", expect_string=r"#")

            net.disconnect()
            print(f"[+] Successfully set admin password to '{NEW_ADMIN_PASS}' on {sw_name}!")

        except Exception as e:
            print(f"[!] Failed to bootstrap {sw_name}: {e}")

if __name__ == "__main__":
    main()