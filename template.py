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
    """Handles all file writing dynamically based on the action type."""
    output_file = os.path.join(SCRIPT_DIR, filename)
    border = "=" * 50

    print(f"   - Appending results to {filename}")    
    with open(output_file, "a") as f:
        f.write(f"{border}\n DEVICE: {hostname} ({host})\n{border}\n")
        f.write(f"=== {log_title.upper()} ===\n{content}\n\n")

def run_task(group_name, action):
    devices = load_inventory(group_name)
    
    # Define task variables dynamically based on the chosen action
    task_mapping = {
        "get_configs": {"file": "d1-get_configs-output.txt", "title": "Configuration Backup"},
        "set_vlans": {"file": "d2-set_vlans-output.txt", "title": "VLAN Deployment Log"},
        "get_vlans": {"file": "d3-get_vlans-output.txt", "title": "VLAN Status Output"},
        "verify_vlan": {"file": "d4-verify_vlan-output.txt", "title": "VLAN Verification Check"}
    }
    
    task = task_mapping[action]

    for device in devices:
        # Separate configuration data from connection data
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
            print(f">>> Connecting to {device['host']} for task: {action}...")
            connection = ConnectHandler(**netmiko_params)
            hostname = connection.find_prompt().strip(" #>").strip()
            
            # --- DYNAMIC EXECUTION ENGINE ---
            if action == "get_configs":
                print(f"   - Retrieving configurations of {hostname}...")
                output = connection.send_command("show configuration")
                
            elif action == "set_vlans":
                commands = [
                    f"create vlan {vlan_name} tag {vlan_tag}",
                    f"configure vlan {vlan_name} ipaddress {vlan_ip}/24"
                ]
                print(f"   - Deploying VLAN configurations on {hostname}...")
                output = connection.send_config_set(commands)
                connection.send_command("save configuration primary")
                print(f"   - Applied and saved VLAN {vlan_name} on {hostname}.")
                
            elif action == "get_vlans":
                print(f"   - Retrieving VLAN configurations for {hostname}...")
                output = connection.send_command("show vlan")
                
            elif action == "verify_vlan":
                print(f"   - Verifying VLAN configurations on {hostname}...")
                command_output = connection.send_command(f"show vlan {vlan_name}")
                required_items = [vlan_name, str(vlan_tag), vlan_ip]

                if all(item in command_output for item in required_items):
                    output = f"SUCCESS: All parameters found for {vlan_name}."
                    print(output)
                else:
                    # Find exactly what went wrong for better troubleshooting
                    missing_items = [item for item in required_items if item not in command_output]
                    output = f"FAILED: Missing fields from output: {missing_items}"
                    print(output)


            # Log the specific results to the correct file
            log_output(task["file"], hostname, device["host"], task["title"], output)

            print(f"<<< Disconnecting from {hostname}")
            connection.disconnect()
            
        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            print(f"Connection Failed for {device['host']}: {e}")
        except Exception as e:
            print(f"Unexpected Error on {device['host']}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-g", "--group", default="access_closet_1", help="Inventory group name")
    
    args = parser.parse_args()
    run_task(args.group)
