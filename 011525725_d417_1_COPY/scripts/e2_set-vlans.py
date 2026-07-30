#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler

# Define our environment and establish where the configuration log results will save
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = os.path.join(SCRIPT_DIR, "e2_set-vlans_output.txt")


def load_inventory(group_name, filename="inventory.yaml"):
    """Reads our YAML inventory file and grabs the specific switch group we ask for."""
    filepath = os.path.join(SCRIPT_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"!!! Inventory file missing: '{filepath}' !!!")
        sys.exit(1)

    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}

    devices = full_inventory.get(group_name)
    if not devices:
        available = ", ".join(full_inventory.keys()) or "None"
        print(f"!!! Group '{group_name}' not found or empty in inventory !!!")
        print(f"    Available groups: {available}")
        sys.exit(1)

    return devices


def set_vlans(group_name):
    """Connects to the devices to dynamically build and push the required VLAN configuration changes."""
    devices = load_inventory(group_name)
    print(f"Found {len(devices)} devices in {group_name}.")

    for device in devices:
        # Pull out our specific target data from the inventory file dictionary
        device_ip = device["host"]
        device_type = device["device_type"]
        vlan_name = device["vlan_name"]
        vlan_tag = device["vlan_tag"]
        vlan_ip = device["vlan_ip"]

        params = {
            "device_type": device_type,
            "host": device_ip,
            "username": device["username"],
            "password": device["password"],
            "ssh_strict": device.get("ssh_strict", False),
            "system_host_keys": device.get("system_host_keys", False),
        }

        # Build our list of precise EXOS CLI commands using variables from our inventory
        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_tag}",
            f"configure vlan {vlan_name} ipaddress {vlan_ip} 255.255.255.0",
        ]

        print(f"Connecting to {device_type} at {device_ip}...")
        try:
            with ConnectHandler(**params) as device_connection:
                hostname = device_connection.find_prompt().strip(" #>").strip()
                print(f"- Connected to {hostname} ({device_ip}). Sending configurations...")

                # Loop through our commands list, execute them, and store the output text
                configurations_set_output = ""
                for cmd in commands:
                    configurations_set_output += f"Command: {cmd}\n"
                    configurations_set_output += device_connection.send_command(cmd) + "\n"

                # Commit our changes permanently to the primary configuration block
                # The 'cancel-dir' flag tells EXOS to overwrite the config instantly without an interactive y/n prompt
                print("- Saving running configuration cleanly to primary partition...")
                configurations_save_output = device_connection.send_command("save configuration primary cancel-dir")

                # Capture a quick verification snapshot to confirm the new VLAN states
                print(f"- Verifying {hostname} VLAN configuration state...")
                configurations_set_status = device_connection.send_command("show vlan")

                # Compile our execution log, saving tracking steps, save logs, and status checks
                border = "=" * 50
                with open(MASTER_FILE, "a") as log_file:
                    log_file.write(f"{border}\n SWITCH: {hostname} ({device_ip})\n{border}\n")
                    log_file.write(f"=== CONFIGURATION LOG ===\n{configurations_set_output}\n\n")
                    log_file.write(f"=== CONFIGURATION SAVE ===\n{configurations_save_output}\n\n")
                    log_file.write(f"=== CONFIGURATION STATUS ===\n{configurations_set_status}\n\n")

                print(f"- Results appended to {os.path.basename(MASTER_FILE)}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set VLAN configurations on network.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    args = parser.parse_args()

    set_vlans(args.group)
