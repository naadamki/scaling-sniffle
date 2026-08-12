import argparse
import os
from network_manager import InventoryManager, DeviceManager

ENV_USER = os.environ.get("DEF_USER", "admin")
ENV_PASS = os.environ.get("DEF_PASS", "")
SVC_USER = os.environ.get("SVC_USER", "netsvc")
SVC_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "service account deployment bootstrap"

def parse_arguments():
    # Handles terminal command line parameters explicitly.
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.", default="N-CoreA-01.yaml")
    p.add_argument("-c", "--closet", help="Specific closet to inspect.", default="Access_Closet_1")
    return p.parse_args()

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    
    for device in inventory.devices:
        hostname = (
            device.get("hostname") or device.get("host") 
            if isinstance(device, dict) 
            else str(device)
        )
        try:
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
                ) as connection:
                
                account_created = connection.create_service_account(SVC_USER, SVC_PASS)
                
                if account_created:
                    print(f"--  Service account '{SVC_USER}' successfully built.")
                    connection.save_config_primary()
                    print(f"--  Saved active configuration state.")
                else:
                    print(f"!!  Failed to deploy account on {connection.hostname}")
                    
        except Exception as e:
            print(f"!!  Process aborted for {hostname}\n !! {e}")
            
    print(f"\nSuccess running {TITLE}!\n")

if __name__ == "__main__":
    main()
