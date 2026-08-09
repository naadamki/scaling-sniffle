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

            net.send_command_timing("enable ssh2")

            net.send_command_timing("configure account admin password")
            net.send_command_timing("")              
            net.send_command_timing(NEW_ADMIN_PASS)   
            net.send_command_timing(NEW_ADMIN_PASS)   

            save_out = net.send_command_timing("save configuration primary")
            if "y/N" in save_out or "?" in save_out or "y/n" in save_out.lower():
                net.send_command_timing("y")

            net.disconnect()
            print(f"[+] Successfully set admin password to '{NEW_ADMIN_PASS}' on {sw_name}!")

        except Exception as e:
            print(f"[!] Failed to bootstrap {sw_name}: {e}")

if __name__ == "__main__":
    main()