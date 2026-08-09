import argparse
import configparser
import sys
import os
import yaml
from network_manager import EXOSManager

env_user = os.environ.get("EXOS_DEFAULT_USER", "admin")
env_pass = os.environ.get("EXOS_DEFAULT_PASS", "1234")
new_pass = os.environ.get("EXOS_PASS_PASS", "4321")

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="Network Device Configuration Backups.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()

def load_switches(file_path, closet_name):
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"    !! Failed to load inventory: {e}")
        sys.exit(1)


def main():
    args = parse_arguments()
    switches = load_switches(args.inventory_file, args.closet)

    for sw in switches:
        try:
            with EXOSManager(sw, username=env_user, password=env_pass) as device:
                try:
                    device.send_config(f"configure account admin password {new_pass}")
                    print(f"    -- Configured new password.")
                except Exception as e:
                    print(f"    !! {e}")

                try:
                    device.save_config_primary()
                    print(f"    -- Saved configuration to device.")
                except Exception as e:
                    print(f"    !! {e}")

        except Exception:
            print(f"    !! Switching to next device...")

if __name__ == "__main__":
    main()










