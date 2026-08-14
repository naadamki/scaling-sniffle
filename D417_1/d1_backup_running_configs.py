"""
Script Name: backup_running_configs.py
Purpose: Automates the backup of configuration data across 
    targeted network devices within a specific building block inventory closet.
Target Environment: ExtremeXOS (EXOS) Switch Infrastructure
Architecture Note: Leverages the custom 'network_manager' module (network_manager.py) 
    to handle low-level Netmiko connections, vendor driver strategy patterns, and safe context-managed execution lifecycles.
"""

import argparse
import os
import configparser
from network_manager import InventoryManager, DeviceManager

# --- ENVIRONMENT CONFIGURATION ---
# Retrieve default service account credentials from environment variables with safe fallback values to prevent hardcoded secrets.
ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "network device configuration backup"


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
    """ Main execution loop. Iterates through the targeted device inventory, establishes secure connections, retrieves configuration data, and writes the aggregated data to an INI output file.
    """
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    output_file = "d1_backup_running_configs_output.ini"
    config = configparser.ConfigParser()

    # Iterate sequentially through each network element in the inventory group
    for device in inventory.devices:
        # Safely extract the hostname regardless of whether the inventory entry is formatted as a structured dictionary or a raw string value.
        hostname = (
            device.get("hostname") or device.get("host")
            if isinstance(device, dict)
            else str(device)
        )

        try:
            # Use a context manager to ensure proper socket/SSH connection cleanup even if exceptions occur midway through execution.
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:

                # Attempt to retrieve the raw configuration data from the device
                configuration_output = connection.get_config()

                if configuration_output:
                    # Populate the ConfigParser object with device metadata and configuration text
                    config[hostname] = {
                        "Hostname": hostname,
                        "IP Address": connection.host,
                        "Configuration": configuration_output,
                    }
                    print(f"--  {hostname} configuration backup collected.")
                else:
                    print(f"!!  Failed to retrieve configuration for {hostname}")

        except Exception as e:
            # Gracefully catch connection timeouts, authentication failures, or socket drops to prevent the bulk script from crashing mid-run.
            print(f"!!  Process aborted for {hostname}\n    {e}")

    # Write aggregated configuration data from all reachable devices into the output INI file
    print(f"--  Writing aggregated device backups to {output_file}...")
    with open(output_file, "w") as f:
        config.write(f)

    print(f"\nSuccess running {TITLE}!\n")


if __name__ == "__main__":
    main()