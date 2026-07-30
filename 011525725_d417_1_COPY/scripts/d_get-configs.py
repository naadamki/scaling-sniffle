#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler

# Figure out exactly where this script is running from so we can save files to the same folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_inventory(group_name, filename="inventory.yaml"):
    """Reads our YAML inventory file and grabs the specific switch group we ask for."""
    filepath = os.path.join(SCRIPT_DIR, filename)
    
    # Safety check: if our inventory file is missing, stop the script immediately
    if not os.path.exists(filepath):
        print(f"!!! Inventory file missing: '{filepath}' !!!")
        sys.exit(1)

    # Open and parse the YAML data safely
    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}

    # Extract just the specific switches we need (like access_closet_1)
    devices = full_inventory.get(group_name)
    if not devices:
        available = ", ".join(full_inventory.keys()) or "None"
        print(f"!!! Group '{group_name}' not found or empty in inventory !!!")
        print(f"    Available groups: {available}")
        sys.exit(1)

    return devices


def get_configurations(group_name):
    """Connects to each switch to download its standalone VLAN table backup file."""
    devices = load_inventory(group_name)

    # Loop through our target switches one by one
    for device in devices:
        device_ip = device["host"]
        device_type = device["device_type"]

        # Package the authentication and connection data for Netmiko
        params = {
            "device_type": device_type,
            "host": device_ip,
            "username": device["username"],
            "password": device["password"],
            "ssh_strict": device.get("ssh_strict", False),
            "system_host_keys": device.get("system_host_keys", False),
        }

        print(f"Connecting to {device_type} at {device_ip}...")
        try:
            # Open the SSH connection and automatically close it when this block finishes
            with ConnectHandler(**params) as device_connection:
                # Capture the switch's command prompt and strip out trailing characters
                hostname = device_connection.find_prompt().strip(" #>").strip()
                print(f"- Connected to {hostname} ({device_ip}).")
                print(f"- Obtaining VLAN configurations for {hostname}.")

                # Run the command to pull the switch configuration state
                command_output = device_connection.send_command("show vlan")

                # Dynamically name the backup file using the switch's unique hostname
                individual_file = os.path.join(SCRIPT_DIR, f"{hostname}_config.txt")

                # Save the configuration out to its own standalone text file
                with open(individual_file, "w") as log_file:
                    log_file.write(command_output + "\n")

                print(f"- Successfully generated standalone file: {os.path.basename(individual_file)}")
                print(f"- Disconnected from {hostname}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")


# Standard entry point to let us run the script directly from the terminal
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get configurations from switches.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    args = parser.parse_args()

    get_configurations(args.group)
