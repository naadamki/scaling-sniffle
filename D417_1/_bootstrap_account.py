import argparse
import sys
import os
import yaml
from network_manager import DeviceManager

ENV_USER = "admin"
ENV_PASS = ""

SERVICE_USER = "net_auto"
SERVICE_PASS = "SC123!"

TITLE = "Service Account Deployment Provisioning Bootstrap"

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
        device_label = device.get("hostname") or device.get("host") if isinstance(device, dict) else str(device)
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                
                account_created = connection.create_service_account(SERVICE_USER, SERVICE_PASS)
                
                if account_created:
                    print(f"  --  Service account '{SERVICE_USER}' successfully built.")
                    connection.save_config_primary()
                    print(f"  --  Saved active configuration state.")
                else:
                    print(f"  !!  Failed to deploy account on {connection.hostname}")
                    
        except Exception as e:
            print(f"  !!  Process aborted for {device_label}\n !! {e}")
            
    print(f"\nSuccess running {TITLE}!\n")

if __name__ == "__main__":
    main()
