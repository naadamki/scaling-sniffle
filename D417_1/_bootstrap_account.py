import argparse
import sys
import os
import yaml
from network_manager import DeviceManager
# from network_manager import EXOSManager

ENV_USER = "admin"
ENV_PASS = ""
NEW_PASS = "1234"

TITLE = "account password configuration bootstrap deployment"

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

    for device in inventory:
        try:
            with DeviceManager(device, device_type=None, username=ENV_USER, password=ENV_PASS) as connection:

                connection.configure_account_password(ENV_USER, ENV_PASS, NEW_PASS)
                print(f"  --  Configured new password.")

                connection.save_config_primary()
                print(f"  --  Saved configuration to device.")

        except Exception as e:
            print(f"  !!  Process aborted for {device['hostname']}\n  !!  {e}")

print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()



