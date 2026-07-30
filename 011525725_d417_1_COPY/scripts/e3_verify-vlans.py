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
MASTER_FILE = os.path.join(OUTPUT_DIR, f"e3_verify-vlans_output.txt")

# Load inventory.yaml file.
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

def verify_vlans(group_name):    
    devices = load_inventory(group_name)
    
    for device in devices:
        device_ip = device["host"]
        device_type = device["device_type"]
        expected_vlan = device["vlan_name"]
        expected_tag = str(device["vlan_tag"])

        params = {
            "device_type": device_type,
            "host": device_ip,
            "username": device["username"],
            "password": device["password"],
            "ssh_strict": device.get("ssh_strict", False),
            "system_host_keys": device.get("system_host_keys", False),
        }        


        command = "show vlan"

        print(f"Connecting to {device_type} at {device_ip}...")

        try:
            device_connection = ConnectHandler(**params)
            hostname = device_connection.find_prompt().strip(" #>").strip()
            print(f"- Connected to {hostname} ({device_ip}).")

            print(f"- Obtaining VLAN configurations for {hostname}.")
            command_output = device_connection.send_command(command)

            vlan_exists = expected_vlan in command_output
            tag_exists = expected_tag in command_output

            if vlan_exists and tag_exists:
                status = "PASS"
                detail = f"VLAN '{expected_vlan}' with Tag {expected_tag} confirmed active."
            else:
                status = "FAIL"
                detail = f"!!! Missing VLAN '{expected_vlan}' or Tag {expected_tag} !!!"

            results = f"[{status} {hostname} ({device_ip}): {detail}]"
            print(results)

            with open(MASTER_FILE, "a") as log_file:
                log_file.write(f"==================================================\n")
                log_file.write(f"{results}\n")
                log_file.write(f"==================================================\n")
            print(f"- Results for {hostname} appended to {MASTER_FILE}.")

            device_connection.disconnect()
            print(f"- Disconnected from {hostname}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify VLAN configurations match.")
    parser.add_argument("-g", "--group", default="access_closet_1", )
    args = parser.parse_args()

    verify_vlans(args.group)