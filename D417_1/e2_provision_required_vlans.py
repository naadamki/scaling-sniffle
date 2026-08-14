"""
Script Name: provision_required_vlans.py
Purpose: Automates the provisioning of required VLANs and port assignments across 
    targeted network devices based on an inventory mapping file.
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

TITLE = "automated VLAN deployment"


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
    Main execution loop. Parses inventory data, builds a required VLAN mapping, 
    and sequentially provisions VLAN IDs, names, and port memberships on each switch.
    """
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    
    # Build a structural map defining which VLANs belong to which devices
    vlan_map = inventory.build_required_vlan_map()

    # Iterate sequentially through each network element in the inventory group
    for device in inventory.devices:
        # Safely extract the hostname regardless of whether the inventory entry 
        # is formatted as a structured dictionary or a raw string value.
        hostname = (
            device.get("hostname") or device.get("host")
            if isinstance(device, dict)
            else str(device)
        )        

        # Check if the current device has any pending VLAN configurations required
        targets_to_provision = vlan_map.get(hostname, [])
        if not targets_to_provision:
            print(f"-- Skipping {hostname}: No provisioning required.")
            continue

        try:
            # Use a context manager to ensure proper socket/SSH connection cleanup 
            # even if exceptions occur midway through execution.
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:

                # Loop through each individual VLAN rule mapped to this device
                for vlan_id, vlan_name, tagged_ports, untagged_ports in targets_to_provision:

                    # Verify if the VLAN already exists; create it if missing
                    if not connection.verify_vlan_exists(vlan_id=vlan_id, vlan_name=vlan_name):
                        connection.create_vlan(vlan_id, vlan_name)
                        print(f"--  {vlan_name} (ID: {vlan_id}) created on {hostname}.")
                    else:
                        print(f"--  {vlan_name} (ID: {vlan_id}) already exists on {hostname}.")

                    # Assign tagged ports if specified and valid
                    if tagged_ports and tagged_ports != "None":
                        connection.add_vlan_ports(vlan_name, tagged_ports, tag=True)

                    # Assign untagged ports if specified and valid
                    if untagged_ports and untagged_ports != "None":
                        connection.add_vlan_ports(vlan_name, untagged_ports, tag=False)

                # Commit running configuration changes to non-volatile primary storage
                connection.save_config_primary()
                print(f"--  Configuration saved successfully for {hostname}.")
                
        except Exception as e:
            # Gracefully catch connection timeouts, authentication failures, or execution errors 
            # to prevent the bulk script from crashing mid-run.
            print(f"!!  Process aborted for {hostname}\n    {e}")

    print(f"\nSuccess running {TITLE}!\n")


if __name__ == "__main__":
    main()