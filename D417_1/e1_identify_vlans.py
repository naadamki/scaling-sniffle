import argparse
import sys
import os
import yaml
from network_manager import DeviceManager

ENV_USER = os.environ.get("DEF_USER", "admin")
ENV_PASS = os.environ.get("DEF_PASS", "")

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
                print(f"  !!  {closet} not in {inventory}")
                sys.exit(1)
    except Exception as e:
        print(f"  !!  Failed to load inventory.")
        print(f"  !!  {e}")
        sys.exit(1)

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
    output_file = "e1_identify_vlans.txt"

    for device in inventory:
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                
                parsed_vlans = connection.get_vlans(structured=True)                
                vlans = [(item["vlan_name"], item["vlan_id"]) for item in parsed_vlans]

                print(f"  --  {connection.hostname} ({connection.host}) VLAN configuration:\n")
                
                for name, id in vlans:
                    print(f"  --  {name} (ID: {id})")
                    
                    with open(output_file, "a") as f:
                        f.write(f"{connection.hostname} ({connection.host}): {vlans}")

        except Exception as e:
            print(f"  !!  Process aborted for {device['hostname']}\n  !!  {e}")


print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()
