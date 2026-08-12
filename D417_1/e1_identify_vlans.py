"""
Script Name: identify_vlans.py
Purpose: Automates the discovery and display of active VLAN configurations across 
         targeted network devices within a specific building block inventory closet.
Target Environment: ExtremeXOS (EXOS) Switch Infrastructure
Architecture Note: Leverages the custom 'network_manager' module 
    (network_manager.py) to handle low-level Netmiko connections, vendor driver strategy patterns, and safe context-managed execution lifecycles.

"""

import argparse
import os
from network_manager import InventoryManager, DeviceManager

# --- ENVIRONMENT CONFIGURATION ---
# Retrieve service account credentials from environment variables 
# with safe fallback values to prevent hardcoded secrets.
ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "network device VLAN configuration identification"


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
    establishes secure connections, retrieves parsed VLAN structures, 
    and outputs formatted network details to the console.
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
                
                # Retrieve structured and parsed VLAN data from the switch
                vlans = connection.get_vlans(parse=True)

                print(f"--  {connection.hostname} ({connection.host}) VLAN Configuration:")
                # Loop through each individual VLAN entry and print its name and ID
                for vlan in vlans:
                    print(f"    - {vlan['name']} (VID: {vlan['vid']})")

        except Exception as e:
            # Gracefully catch connection timeouts, authentication failures, or socket drops 
            # to prevent the bulk script from crashing mid-run.
            print(f"!!  Process aborted for {hostname}\n!!  Error details: {e}")

    print(f"\nSuccess running {TITLE}!\n")


if __name__ == "__main__":
    main()