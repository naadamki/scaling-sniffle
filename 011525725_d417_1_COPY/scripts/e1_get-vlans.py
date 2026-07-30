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
MASTER_FILE = os.path.join(OUTPUT_DIR, f"e1_get-vlans_output.txt")




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

def get_vlans(group_name):    
    devices = load_inventory(group_name)
    
    for device in devices:
        device_ip = device["host"]
        device_type = device["device_type"]

        params = {
            "device_type": device_type,
            "host": device_ip,
            "username": device["username"],
            "password": device["password"],
            "ssh_strict": device.get("ssh_strict", False),
            "system_host_keys": device.get("system_host_keys", False),
        }        


        command = "show configuration"

        print(f"Connecting to {device_type} at {device_ip}...")

        try:
            device_connection = ConnectHandler(**params)
            hostname = device_connection.find_prompt().strip(" #>").strip()
            print(f"- Connected to {hostname} ({device_ip}).")

            print(f"- Obtaining configurations for {hostname}.")
            command_output = device_connection.send_command(command)

            with open(MASTER_FILE, "a") as log_file:
                log_file.write(f"==================================================\n")
                log_file.write(f" SWITCH: {hostname} ({device_ip})\n")
                log_file.write(f"==================================================\n")
                log_file.write(command_output + "\n\n")
            print(f"- Appended {hostname} to {MASTER_FILE}.")

            device_connection.disconnect()
            print(f"- Disconnected from {hostname}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get VLANs configured on network.")
    parser.add_argument("-g", "--group", default="access_closet_1", )
    args = parser.parse_args()

    get_vlans(args.group)