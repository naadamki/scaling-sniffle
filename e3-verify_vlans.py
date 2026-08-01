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
        f.write(f"=== {log_title.upper()} ===\n{content}\n\n")

def run_task(group_name):
    devices = load_inventory(group_name)

    for device in devices:
        device_type = device["device_type"]
        ip = device["host"]
        vlan_name = device.get("vlan_name")
        vlan_tag = device.get("vlan_tag")
        vlan_ip = device.get("vlan_ip")
        
        netmiko_params = {
            "device_type": device["device_type"],
            "host": device["host"],
            "username": device["username"],
            "password": device["password"],
        }

        
        try:
            print(f">>> Connecting to {device['host']} to verify VLAN configuration...")
            connection = ConnectHandler(**netmiko_params)
            hostname = connection.find_prompt().strip(" #>").strip()
            
            output = connection.send_command(f"show vlan {vlan_name}")

            required_items = [vlan_name, str(vlan_tag), vlan_ip]

            if all(item in output for item in required_items):
                verification_status = f"SUCCESS: All parameters found for {vlan_name} on {hostname} {device_type} ({ip})."
                print(verification_status)
            else:
                missing_items = [item for item in required_items if item not in output]
                verification_status = f"FAILED: {hostname} {device_type} ({ip}) is missing fields: {missing_items}"
                print(verification_status)

            full_log = f"{verification_status} - {hostname} {device_type} ({ip})\n\n--- Raw Switch Output ---\n{output}"
            
            log_output("e3-verify_vlans-output.txt", hostname, device["host"], "VLAN verification check", full_log)
            connection.disconnect()
            
        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            print(f"Connection Failed for {device['host']}: {e}")
        except Exception as e:
            print(f"Unexpected Error on {device['host']}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify VLAN configuration.")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    
    args = parser.parse_args()
    run_task(args.group)
