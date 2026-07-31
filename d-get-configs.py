#!/usr/bin/env python3
import os                           # File creation
import sys                          # Error handling
import yaml                         # Inventory.yaml handling
import argparse                     # Group choice for future additions
import logging                      # Information and logging
from netmiko import ConnectHandler  # Connection handling


# Where script is ran
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Logger for logging
log_format = "%(asctime)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=logging.INFO,                       
    format=log_format,
    handlers=[
        logging.FileHandler("app.log"),       
        logging.StreamHandler()               
    ]
)

LOG = logging.getLogger(__name__)





def load_inventory(group_name, filename="inventory.yaml"):
    """ Reads YAML inventory file. """
    filepath = os.path.join(SCRIPT_DIR, filename)

    # Stop script if inventory file not found
    if not os.path.exists(filepath):
        LOG.critical(f"!!! Inventory file missing '{filepath}'.")
        sys.exit(1)

    # Open and parse the YAML file
    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}

    # Extract just the specified group in YAML file
    devices = full_inventory.get(group_name)
    if not devices:
        available = ", ".join(full_inventory.keys()) or "None"
        LOG.error(f"!! Group '{group_name}' not found or empty inventory.")
        LOG.info(f"      Available groups: {available}")
        sys.exit(1)

    return devices


def get_configurations(group_name):
    """ Connects and downloads configurations. """
    devices = load_inventory(group_name)

    # Loop through devices one by one
    for device in devices:
        ip = device["host"]
        type = device["device_type"]

        # Separate connection data for Netmiko
        netmiko_params = {
            "device_type": type,
            "host": ip,
            "username": device["username"],
            "password": device["password"],
            "ssh_strict": device.get("ssh_strict", False),
            "system_host_keys": device.get("system_host_keys", False),
        }

        LOG.info(f"Connecting to {type} at {ip}...")
        try:
            # Open SSH connection
            with ConnectHandler(**netmiko_params) as connection:

                # Capture switch's command prompt
                hostname = connection.find_prompt().strip("#>").strip()
                LOG.info(f"- Connected to {hostname} ({ip}).")

                # Capture output from sent command
                LOG.info(f"- Obtaining configurations for {hostname}...")    
                command_output = connection.send_command("show configuration")

                # File to write configurations to
                individual_file = os.path.join(SCRIPT_DIR, f"d-{hostname}_config.txt")

                # Write configurations to file
                with open(individual_file, "w") as log_file:
                    log_file.write(command_output + "\n")

                LOG.info(f"- Successfully generated file: {os.path.basename(individual_file)}.")
                LOG.info(f"- Disconnected from {hostname}.\n")

        # Handle inability to connect
        except Exception as e:
            LOG.exception(f"!! Failed to connect to {ip}: {e} \n")



# Standard entry point for script to run directly from the terminal
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Get configurations from switches.")
    p.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    args = p.parse_args()

    get_configurations(args.group)