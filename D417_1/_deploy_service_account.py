"""
Script Name: deploy_service_account.py
Purpose: Automates the provisioning of administrative service accounts across 
         targeted network devices within a specific building block inventory closet.
Target Environment: ExtremeXOS (EXOS) Switch Infrastructure
Architecture Note: Leverages the custom 'network_manager' module 
    (network_manager.py) to handle low-level Netmiko connections, vendor driver strategy patterns, and safe context-managed execution lifecycles.
"""

import argparse
import os
from network_manager import InventoryManager, DeviceManager

# --- ENVIRONMENT CONFIGURATION ---
# Retrieve default administrative credentials and target service account details 
# from environment variables with safe fallback values to prevent hardcoded secrets.
ENV_USER = os.environ.get("DEF_USER", "admin")
ENV_PASS = os.environ.get("DEF_PASS", "")
SVC_USER = os.environ.get("SVC_USER", "netsvc")
SVC_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "service account deployment"


def parse_arguments():
    """
    Handles command-line parameters to allow dynamic inventory specification 
    and target closet filtering during execution.
    """
    parser = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    parser.add_argument(
        "-i", "--inventory", 
        help="Building Block YAML inventory file path.", 
        default="N-CoreA-01.yaml"
    )
    parser.add_argument(
        "-c", "--closet", 
        help="Specific target closet group to inspect from inventory.", 
        default="Access_Closet_1"
    )
    return parser.parse_args()


def main():
    """
    Main execution loop. Iterates through the targeted device inventory, 
    establishes secure connections, provisions the service account, and 
    persists the active configuration state to primary flash.
    """
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    
    # Iterate sequentially through each network element in the inventory group
    for device in inventory.devices:
        # Safely extract the hostname regardless of whether the inventory entry 
        # is formatted as a structured dictionary or a raw string value.
        hostname = (
            device.get("hostname") or device.get("host") 
            if isinstance(device, dict) 
            else str(device)
        )
        
        try:
            # Use a context manager to ensure proper socket/SSH connection cleanup 
            # even if exceptions occur midway through execution.
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:
                
                # Attempt to provision the service account
                account_created = connection.create_account(username=SVC_USER, password=SVC_PASS, access_level="admin")
                
                if account_created:
                    print(f"--  Service account '{SVC_USER}' successfully built on {hostname}.")
                    # Commit running configuration to non-volatile primary storage
                    connection.save_config_primary()
                    print(f"--  Saved active configuration state for {hostname}.")
                else:
                    print(f"!!  Failed to deploy account on {connection.hostname}")
                    
        except Exception as e:
            # Gracefully catch connection timeouts, authentication failures, or socket drops 
            # to prevent the bulk script from crashing mid-run.
            print(f"!!  Process aborted for {hostname}\n !! Error details: {e}")
            
    print(f"\nSuccess running {TITLE}!\n")


if __name__ == "__main__":
    main()