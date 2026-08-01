import os
import sys
import yaml
import argparse
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_inventory(group_name, filename="inventory.yaml"):
    """Loads and returns the device list from the YAML file."""
    filepath = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(filepath):
        print(f"!!! Inventory file missing '{filepath}'.")
        sys.exit(1)
        
    with open(filepath, "r") as f:
        full_inventory = yaml.safe_load(f) or {}
        
    devices = full_inventory.get(group_name)
    if not devices:
        available = ", ".join(full_inventory.keys()) or "None"
        print(f"ERROR: Group '{group_name}' not found. Available: {available}")
        sys.exit(1)
    return devices

def log_output(filename, hostname, host, log_title, content):
    output_file = os.path.join(SCRIPT_DIR, filename)
    border = "=" * 50
    with open(output_file, "a") as f:
        f.write(f"{border}\n DEVICE: {hostname} ({host})\n{border}\n")
        f.write(f"=== {log_title.upper()} ===\n{content}\n\n")

def run_task(group_name):
    devices = load_inventory(group_name)

    for device in devices:
        netmiko_params = {
            "device_type": device["device_type"],
            "host": device["host"],
            "username": device["username"],
            "password": device["password"],
        }
        
        try:
            print(f">>> Connecting to {device['host']} to get configuration...")
            connection = ConnectHandler(**netmiko_params)
            hostname = connection.find_prompt().strip(" #>").strip()
            output = connection.send_command("show configuration")

            # Log the specific results to the correct file
            log_output("d1-get_configs-output.txt", hostname, device["host"], "Configuration Backup", output)
            connection.disconnect()
            
        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            print(f"Connection Failed for {device['host']}: {e}")
        except Exception as e:
            print(f"Unexpected Error on {device['host']}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup configurations.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    
    args = parser.parse_args()
    run_task(args.group)
