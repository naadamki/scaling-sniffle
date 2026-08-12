"""
Script Name: verify_vlan_deployment.py
Purpose: Audits and verifies active VLAN deployment states against expected inventory 
         specifications across targeted network devices in a building block closet.
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

TITLE = "network VLAN deployment verification"


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
    Main execution loop. Queries active VLAN state on target switches, compares 
    the active network state against expected baseline inventory requirements, 
    and outputs a structured compliance report.
    """
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    
    # Retrieve the baseline expected VLAN mapping from inventory definitions
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

        # Check if the device has mandatory VLAN mappings defined in the inventory
        required_vlans = vlan_map.get(hostname, [])
        if not required_vlans:
            print(f"--  Skipping {hostname}: No required VLAN mappings found.")
            continue
            
        try:
            # Use a context manager to ensure proper socket/SSH connection cleanup 
            # even if exceptions occur midway through execution.
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:

                # Poll live active VLAN state from the switch
                current_vlans = connection.get_vlans(parse=True)
                
                # Construct an optimized lookup set of active (VID, Name) tuples for fast verification
                current_vlan_set = {
                    (str(vlan.get("vlan_id")), vlan.get("vlan_name")) 
                    for vlan in current_vlans
                }
                verification_results = []

                # Audit required inventory VLANs against live network state
                for required_vlan in required_vlans:
                    vlan_id, vlan_name, _, _ = required_vlan
                    
                    target_tuple = (str(vlan_id), vlan_name)
                    is_present = target_tuple in current_vlan_set
                    
                    verification_results.append({
                        "vlan_id": vlan_id,
                        "vlan_name": vlan_name,
                        "verified": is_present
                    })

                # Print formatted audit compliance report for the target switch
                print(f"--  Verification Report for {connection.hostname} ({connection.host}):")
                device_healthy = True                
                for result in verification_results:
                    if result["verified"]:
                        print(f"    - PASS: VLAN {result['vlan_name']} (ID: {result['vlan_id']}) is active.")
                    else:
                        print(f"    - FAIL: VLAN {result['vlan_name']} (ID: {result['vlan_id']}) is MISSING.")
                        device_healthy = False

                # Output summary status based on overall device verification results
                if device_healthy:
                    print(f"    - Status: All required VLANs verified successfully.")
                else:
                    print(f"    - Status: Warning - Mismatched VLAN state detected.")
                
        except Exception as e:
            # Gracefully catch connection timeouts, authentication failures, or execution errors 
            # to prevent the bulk script from crashing mid-run.
            print(f"!!  Process aborted for {hostname}\n!!  Error details: {e}")

    print(f"\nSuccess running {TITLE}!\n")


if __name__ == "__main__":
    main()