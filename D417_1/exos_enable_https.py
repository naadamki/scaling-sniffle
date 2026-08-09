import argparse
import os
import sys
import yaml
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
    args = parse_arguments()
    devices = load_devices(args.inventory_file, args.closet)

    for device in devices:
        host_ip = device.get("host")
        hostname = device.get("hostname", host_ip)
        print(f"Enabling HTTPS on {hostname} ({host_ip})...")

        try:
            # Connect via Netmiko
            connection = ConnectHandler(
                device_type=device.get("device_type", "extreme_exos"),
                host=host_ip,
                username=ENV_USER,
                password=ENV_PASS,
                disabled_algorithms=dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
            )

            commands = [
                "configure ssl certificate privkeylen 2048 country US organization Lab common-name exos.local",
                "enable web https"
            ]

            # 1. Send config block with cmd_verify=False and an extended read_timeout for key generation
            connection.send_config_set(
                commands,
                cmd_verify=False,
                config_mode_command="",
                read_timeout=60
            )

            # 2. Save configuration and confirm prompt
            save_out = connection.send_command_timing("save configuration primary")
            if "(y/n)" in save_out.lower() or "?" in save_out or "save configuration to" in save_out.lower():
                connection.send_command_timing("y")

            connection.disconnect()
            print(f"    -- Successfully enabled HTTPS and saved config on {hostname} ({host_ip}).\n")

        except Exception as e:
            print(f"    !! Failed to enable HTTPS on {hostname} ({host_ip}): {e}\n")


if __name__ == "__main__":
    main()