import argparse
import sys
import os
import yaml
from network_manager import EXOSManager

env_user = os.environ.get("EXOS_DEFAULT_USER", "admin")
env_pass = os.environ.get("EXOS_DEFAULT_PASS", "")

NEW_ADMIN_PASS = "1234"


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

    print("\nStarting network device account bootstrapping...")    
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"    !! ERROR: '{args.closet}' not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]

    for sw in all_devices:
        sw_name = sw.get("hostname", sw) if isinstance(sw, dict) else sw
        
        try:
            with EXOSManager(sw, username=env_user, password=env_pass) as connection:
                # 1. Update password
                connection.send_cmd(f"configure account admin password {NEW_ADMIN_PASS}")

                # 2. Save configuration directly (no prompt expected)
                connection.send_cmd("save configuration")

                print(f"Successfully bootstrapped {sw_name}")

        except Exception as e:
            print(f"Failed on {sw_name}: {e}")

if __name__ == "__main__":
    main()