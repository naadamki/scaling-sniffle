#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# Figure out exactly where this script is running from so we can save files to the same folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging - logs to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, 'config_backup.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_inventory(group_name, filename="inventory.yaml"):
    """Reads our YAML inventory file and grabs the specific switch group we ask for."""
    filepath = os.path.join(SCRIPT_DIR, filename)
    
    # Safety check: if our inventory file is missing, stop the script immediately
    if not os.path.exists(filepath):
        logger.error(f"Inventory file missing: '{filepath}'")
        sys.exit(1)

    # Open and parse the YAML data safely
    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}

    # Extract just the specific switches we need (like access_closet_1)
    devices = full_inventory.get(group_name)
    if not devices:
        available = ", ".join(full_inventory.keys()) or "None"
        logger.error(f"Group '{group_name}' not found or empty in inventory")
        logger.error(f"Available groups: {available}")
        sys.exit(1)

    logger.info(f"Loaded {len(devices)} device(s) from group '{group_name}'")
    return devices


def connect_and_backup_device(device):
    """
    Connects to a single switch, retrieves its config, and saves it to a file.
    This function runs in a separate thread.
    """
    device_ip = device["host"]
    device_type = device["device_type"]

    # Package the authentication and connection data for Netmiko
    params = {
        "device_type": device_type,
        "host": device_ip,
        "username": device["username"],
        "password": device["password"],
        "ssh_strict": device.get("ssh_strict", False),
        "system_host_keys": device.get("system_host_keys", False),
    }

    try:
        logger.info(f"Connecting to {device_type} at {device_ip}...")
        
        # Open the SSH connection and automatically close it when this block finishes
        with ConnectHandler(**params) as device_connection:
            # Capture the switch's command prompt and strip out trailing characters
            hostname = device_connection.find_prompt().strip(" #>").strip()
            logger.info(f"Connected to {hostname} ({device_ip})")
            logger.info(f"Obtaining configurations for {hostname}")

            # Run the command to pull the switch configuration state
            command_output = device_connection.send_command("show configuration")

            # Dynamically name the backup file using the switch's unique hostname
            individual_file = os.path.join(SCRIPT_DIR, f"{hostname}_config.txt")

            # Save the configuration out to its own standalone text file
            with open(individual_file, "w", encoding="utf-8") as log_file:
                log_file.write(command_output + "\n")

            logger.info(f"Successfully generated: {os.path.basename(individual_file)}")
            logger.info(f"Disconnected from {hostname}")
            
            return True, hostname, device_ip

    except NetmikoAuthenticationException as e:
        logger.error(f"Authentication failed on {device_ip}: {e}")
        return False, None, device_ip
    except NetmikoTimeoutException as e:
        logger.error(f"Connection timeout on {device_ip}: {e}")
        return False, None, device_ip
    except Exception as e:
        logger.error(f"Unexpected error on {device_ip}: {e}")
        return False, None, device_ip


def get_configurations(group_name, max_workers=5):
    """
    Connects to each switch in parallel to download configurations.
    
    Args:
        group_name: The inventory group to target
        max_workers: Number of parallel threads (default 5)
    """
    devices = load_inventory(group_name)
    
    logger.info(f"Starting parallel backup with {max_workers} worker threads")
    
    # Track results
    successful = []
    failed = []
    
    # Use ThreadPoolExecutor to connect to multiple switches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all devices to the thread pool
        futures = {executor.submit(connect_and_backup_device, device): device for device in devices}
        
        # Process results as they complete (not necessarily in order)
        for future in as_completed(futures):
            try:
                success, hostname, device_ip = future.result()
                if success:
                    successful.append(hostname)
                else:
                    failed.append(device_ip)
            except Exception as e:
                logger.error(f"Thread execution error: {e}")
                failed.append(futures[future]["host"])
    
    # Print summary
    logger.info("=" * 60)
    logger.info(f"BACKUP COMPLETE - Successful: {len(successful)}, Failed: {len(failed)}")
    if successful:
        logger.info(f"Successful backups: {', '.join(successful)}")
    if failed:
        logger.warning(f"Failed backups: {', '.join(failed)}")
    logger.info("=" * 60)


# Standard entry point to let us run the script directly from the terminal
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get configurations from switches in parallel.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    parser.add_argument("-w", "--workers", type=int, default=5, help="Number of parallel threads (default: 5)")
    args = parser.parse_args()

    try:
        get_configurations(args.group, max_workers=args.workers)
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Script failed: {e}")
        sys.exit(1)