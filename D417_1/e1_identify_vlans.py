import argparse
import sys
import os
import yaml
from network_manager import EXOSManager

env_user = os.environ.get("EXOS_DEFAULT_USER", "admin")
env_pass = os.environ.get("EXOS_DEFAULT_PASS", "")

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="Network Device VLAN Configuration Retrieval.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()

def load_inventory(file_path):
    """Safely opens and reads the YAML architecture file."""
    try:
        with open(file_path, "r") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(f"!! YAML parsing error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"!! '{file_path}' not found.")
        sys.exit(1)

def main():
    args = parse_arguments()

    print("\n")
    print(f"Starting network device VLAN configuration retrieval...")    
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"    !! ERROR: '{args.closet}' not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]

    for sw in all_devices:
        try:    
            with EXOSManager(sw, username=env_user, password=env_pass) as device:

                output = device.get_vlans()

                print(f"    -- {device.hostname} ({device.host}) VLAN configuration:\n")
                print(f"    -- {output}")

        except Exception:
            print(f"-- Skipping to next device...")
            continue

    print(f"Success! VLAN configuration retrieval complete.")
    print("\n")


if __name__ == "__main__":
    main()
