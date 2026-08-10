import argparse
import sys
import os
import yaml
from network_manager import DeviceManager

ENV_USER = "admin"
ENV_PASS = ""  # The target switches currently have a blank admin password

# Define your persistent automation account credentials here
SERVICE_USER = "net_automation"
SERVICE_PASS = "SecureAutomationPassword2026!"

TITLE = "Service Account Deployment Provisioning Bootstrap"

# ... keep your standard parse_arguments() and load_inventory() functions exactly as they were ...

def main():
    print(f"\nStarting {TITLE}...")
    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
    
    for device in inventory:
        device_label = device.get("hostname") or device.get("host") if isinstance(device, dict) else str(device)
        try:
            # 1. Connect using the completely open, blank admin password
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                
                # 2. Deploy your new persistent service account cleanly via send_config
                account_created = connection.create_service_account(SERVICE_USER, SERVICE_PASS)
                
                if account_created:
                    print(f" -- Service account '{SERVICE_USER}' successfully built.")
                    connection.save_config_primary()
                    print(f" -- Saved active configuration state.")
                else:
                    print(f" !! Failed to deploy account on {connection.hostname}")
                    
        except Exception as e:
            print(f" !! Process aborted for {device_label}\n !! {e}")
            
    print(f"\nSuccess running {TITLE}!\n")

if __name__ == "__main__":
    main()
