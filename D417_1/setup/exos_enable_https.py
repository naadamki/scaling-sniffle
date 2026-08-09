import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler

ENV_USER = os.environ.get("EXOS_DEFAULT_USER", "admin")
ENV_PASS = os.environ.get("EXOS_DEFAULT_PASS", "")

def parse_arguments():
    # Handles parameters pushed from CLI
    p = argparse.ArgumentParser(description="Enable HTTPS on EXOS Switches")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()    

def load_devices(file_path, closet_name):
    # Load specified closet from inventory in file_path
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"!! Failed to load inventory: {e}")
        sys.exit(1)

def main():
    # Pull parameters presented in script run into args variable
    args = parse_arguments()

    # Pull inventory's list of devices to be managed
    devices = load_devices(args.inventory_file, args.closet)

    # Cycle through each device in the closet
    for device in devices:
        host_ip = device.get("host")
        print(f"Enabling HTTPS on {device.get('hostname', host_ip)} ({host_ip})...")

        try:
            # Connect via Netmiko
            connection = ConnectHandler(
                device_type=device.get("device_type", "extreme_exos"),
                host=host_ip,
                username=ENV_USER,
                password=ENV_PASS,
                disabled_algorithms=dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
            )

            # Generate Cert & Enable HTTPS
            connection.send_command("configure ssl certificate privkeylen 2048 country US organization Lab common-name exos.local")
            connection.send_command("enable web https")

            # Save configuration & answer prompt
            save_out = connection.send_command_timing("save configuration primary")
            if "y/n" in save_out.lower() or "?" in save_out:
                connection.send_command_timing("y")

            connection.disconnect()
            print(f"    -- Successfully enabled HTTPS and saved config on {host_ip}.\n")

        except Exception as e:
            print(f"    !! Failed to enable HTTPS on {host_ip}: {e}\n")

if __name__ == "__main__":
    main()