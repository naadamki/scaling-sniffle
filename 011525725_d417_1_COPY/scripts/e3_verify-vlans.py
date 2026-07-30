#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler

# Define working directory and output paths (saving everything to the same directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_FILE = os.path.join(SCRIPT_DIR, "e3_verify-vlans_output.txt")


def load_inventory(group_name, filename="inventory.yaml"):
    """Loads and validates the YAML inventory file for the specified group."""
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


def verify_vlans(group_name):
    """Connects to devices in a group and verifies if the expected VLANs exist."""
    devices = load_inventory(group_name)

    for device in devices:
        device_ip = device["host"]
        device_type = device["device_type"]
        expected_vlan = device.get("vlan_name", "")
        expected_tag = str(device.get("vlan_tag", ""))

        # Consolidate Netmiko connection parameters cleanly
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
            with ConnectHandler(**params) as device_connection:
                hostname = device_connection.find_prompt().strip(" #>").strip()
                print(f"- Connected to {hostname} ({device_ip}). Checking VLANs...")

                command_output = device_connection.send_command("show vlan")

                # Verify if both the name and tag exist in the output text
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

                # Write results using a clean separator
                border = "=" * 50
                with open(MASTER_FILE, "a") as log_file:
                    log_file.write(f"{border}\n{results}\n{border}\n")

                print(f"- Results appended to {os.path.basename(MASTER_FILE)}.\n")

        except Exception as e:
            print(f"!!! Failed to connect to {device_ip}: {e} !!!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify VLAN configurations match.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    args = parser.parse_args()

    verify_vlans(args.group)
