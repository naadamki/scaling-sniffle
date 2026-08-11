import argparse
import sys
import os
import re
import yaml
from network_manager import DeviceManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "")

TITLE = "network device VLAN configuration identification"

def parse_arguments():
    # Handles terminal command line parameters explicitly.
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.", default="N-CoreA-01.yaml")
    p.add_argument("-c", "--closet", help="Specific closet to inspect.", default="Access_Closet_1")
    return p.parse_args()

def load_inventory(inventory, closet):
    try:
        with open(inventory, "r") as f:
            data = yaml.safe_load(f)
            try:
                return data["inventory"][closet]
            except:
                print(f"!!  {closet} not in {inventory}")
                sys.exit(1)
    except Exception as e:
        print(f"!!  Failed to load inventory.")
        print(f"!!  {e}")
        sys.exit(1)

import re


def parse_exos_vlan(raw_cli_output):
    vlan_list = []

    pattern = re.compile(
        r"^(?P<name>\S+)\s+"
        r"(?P<vid>\d+)\s+"
        r"(?:(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+)?\s*"
        r"(?:/(?P<mask>\d+)\s+)?\s*"
        r"(?P<flags>[-a-zA-Z]{27})\s+"
        r"(?P<protocol>\S+)\s+"
        r"(?P<active_ports>\d+)\s*/(?P<total_ports>\d+)\s+"
        r"(?P<vr>\S+)",
        re.MULTILINE,
    )

    for match in pattern.finditer(raw_cli_output):
        vlan_data = match.groupdict()
        if vlan_data["ip"] and vlan_data["mask"]:
            vlan_data["ip_address"] = f"{vlan_data['ip']}/{vlan_data['mask']}"
        else:
            vlan_data["ip_address"] = None
        del vlan_data["ip"]
        del vlan_data["mask"]
        vlan_list.append(vlan_data)
    return vlan_list        

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
    output_file = "e1_identify_vlans_output.txt"

    for device in inventory:
        device_label = device.get("hostname") or device.get("host") if isinstance(device, dict) else str(device)
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:                
                raw_vlans = connection.get_vlans()                
                parsed_vlans = parse_exos_vlan(raw_vlans)
                print(f"--  {connection.hostname} ({connection.host}) VLAN configuration:\n")

                print(parsed_vlans)                

        except Exception as e:
            print(f"!!  Process aborted for {device_label}\n!!  {e}")


print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()
