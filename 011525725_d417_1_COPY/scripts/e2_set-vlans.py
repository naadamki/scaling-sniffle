#!/usr/bin/env python3

import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler

# Define script and output directory locations.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define master file to append all command outputs to.
MASTER_FILE = os.path.join(OUTPUT_DIR, f"e2_set-vlans_output.txt")




def load_inventory(group_name, filename="inventory.yaml"):
    filepath = os.path.join(SCRIPT_DIR, filename)

    if not os.path.exists(filepath):
        print(f"!!! Inventory file '{filepath}' not found !!!")
        sys.exit(1)

    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}

    devices = full_inventory.get(group_name)
    
    if not devices:
        available = ", ".join(full_inventory.keys()) if full_inventory else "None"
        print(f"!!! Group '{group_name}' not found or empty in inventory !!!")
        print(f"    Available groups: {available}")
        sys.exit(1)

    return devices

def set_vlans(group_name):    
    devices = load_inventory(group_name)
    print(f"len{devices} found in {group_name}.")
    
    for device in devices:
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

        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_tag}",
            f"configure vlan {vlan_name} ipaddress {vlan_ip} 255.255.255.0",
        ]

        print(f"Connecting to {device_type} at {device_ip}...")
        try:
            device_connection = ConnectHandler(**params)
            hostname = device_connection.find_prompt().strip(" #>").strip()
            print(f"- Connected to {hostname} ({device_ip}).")

            print(f"- Sending configurations to {hostname}...")
            configurations_set_output = ""
            for cmd in commands:
                configurations_set_output += f"Command: {cmd}\n"
                configurations_set_output += device_connection.send_command(cmd) + "\n"

            print(f"- Saving running configuration...")
            configurations_save_output = device_connection.save_config(
                cmd='save configuration primary',
                confirm=True,
                confirm_response='y'
            )

            print(f"- Verifying {hostname} VLAN configuration...")
            configurations_set_status = device_connection.send_command("show vlan")

            with open(MASTER_FILE, "a") as log_file:
                log_file.write(f"==================================================\n")
                log_file.write(f" SWITCH: {hostname} ({device_ip})\n")
                log_file.write(f"==================================================\n")
                log_file.write(f"=== CONFIGURATION LOG ===\n")
                log_file.write(configurations_set_output + "\n\n")
                log_file.write(f"=== CONFIGURATION SAVE ===\n")
                log_file.write(configurations_save_output + "\n\n")
                log_file.write(f"=== CONFIGURATION STATUS ===\n")
                log_file.write(configurations_set_status)
            print(f"- Appended {hostname} to {MASTER_FILE}.")

            device_connection.disconnect()
            print(f"- Disconnected from {hostname}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set VLAN configurations on network.")
    parser.add_argument("-g", "--group", default="access_closet_1", )
    args = parser.parse_args()

    set_vlans(args.group)