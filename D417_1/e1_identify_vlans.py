import argparse
import sys
import os
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

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
    output_file = "e1_identify_vlans_output.txt"

    for device in inventory:
        device_label = device.get("hostname") or device.get("host") if isinstance(device, dict) else str(device)
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:                
                parsed_vlans = connection.get_vlans(structured=True)                

                print(f"--  {connection.hostname} ({connection.host}) VLAN configuration:\n")

                print(parsed_vlans)                

        except Exception as e:
            print(f"!!  Process aborted for {device_label}\n!!  {e}")


print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()
