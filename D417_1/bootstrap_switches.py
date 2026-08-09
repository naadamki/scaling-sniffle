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
                    # Access underlying Netmiko object to use timing-based execution
                    net = connection.connection if hasattr(connection, 'connection') else connection
                    
                    print(f"    -- Updating password on {sw_name}...")
                    
                    # 1. Start interactive password change
                    out = net.send_command_timing("configure account admin password")
                    
                    # 2. Send blank current password (Enter)
                    out += net.send_command_timing("")
                    
                    # 3. Send new password
                    out += net.send_command_timing(NEW_ADMIN_PASS)
                    
                    # 4. Confirm new password
                    out += net.send_command_timing(NEW_ADMIN_PASS)
                    
                    # 5. Save configuration
                    save_out = net.send_command_timing("save configuration primary")
                    if "y/N" in save_out or "?" in save_out or "y/n" in save_out.lower():
                        net.send_command_timing("y")
                    else:
                        net.send_command_timing("save configuration")

                    print(f"    -- Successfully bootstrapped {sw_name}")

            except Exception as e:
                print(f"    !! Bootstrap failed on {sw_name}: {e}")

if __name__ == "__main__":
    main()