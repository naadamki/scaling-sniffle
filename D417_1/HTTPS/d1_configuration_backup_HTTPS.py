import argparse
import json
import os
import sys
import yaml
from network_manager import EXOSHTTPSManager

ENV_USER = os.environ.get("EXOS_DEFAULT_USER", "admin")
ENV_PASS = os.environ.get("EXOS_DEFAULT_PASS", "")


def parse_arguments():
    # Handles parameters pushed from CLI
    p = argparse.ArgumentParser(description="Network Device Configuration Backups.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()    


def load_devices(file_path, closet_name):
    # Load specified closet from inventory in file_path
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"    !! Error loading inventory file '{file_path}': {e}")
        sys.exit(1)


def main():
    args = parse_arguments()
    devices = load_devices(args.inventory_file, args.closet)

    config_backup_file = "d1_configuration_backup_output.json"
    master_backup = []

    print(f"\nStarting configuration backup for closet '{args.closet}'...")

    # Cycle through each device in the closet
    for device in devices:
        host_ip = device.get("host") if isinstance(device, dict) else str(device)
        hostname = device.get("hostname", host_ip) if isinstance(device, dict) else host_ip

        try:
            with EXOSHTTPSManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                config_data = connection.get_config()

                # Parse JSON string back into a Python object if needed
                if isinstance(config_data, str):
                    config_data = json.loads(config_data)

                # Structure hostname, ip, and configs
                device_entry = {
                    "hostname": hostname,
                    "ip": host_ip,
                    "configs": config_data
                }

                master_backup.append(device_entry)
                print(f"    -- Retrieved configuration for {hostname} ({host_ip})")

        except Exception as e:
            print(f"    !! Failed to backup {hostname} ({host_ip}): {e}")
            continue

    try:
        with open(config_backup_file, "w") as config_file:
            json.dump(master_backup, config_file, indent=2)
        print(f"\nSUCCESS: Master backup written successfully to '{config_backup_file}'")
    except Exception as e:
        print(f"\nFAIL: Failed to write backup output file: {e}")


if __name__ == "__main__":
    main()