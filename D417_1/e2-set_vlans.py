import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="Automated VLAN Deployment Engine.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to configure.")
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

def is_reachable(ip):
    """Performs a single ICMP ping check. True if online, False if offline."""
    param = "-n" if subprocess.os.name == "nt" else "-c"
    command = ["ping", param, "1", "-W", "2", ip]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def connect_to(device):
    """Establishes an SSH connection handle using Netmiko."""
    profile = {
        "device_type": device["device_type"],
        "host": device["host"],
        "username": device["username"],
        "password": device["password"],
    }
    try:
        return ConnectHandler(**profile)
    except NetmikoAuthenticationException:
        print(f"Authentication failed for {device['device_type']} at {device['host']}")
        return False
    except NetmikoTimeoutException:
        print(f"Timeout connecting to {device['device_type']} at {device['host']}")
        return False
    except Exception as e:
        print(f"Connection error to {device['host']}: {e}")
        return False

def push_commands(connection, commands):
    """Pushes a list of configuration commands across an open Netmiko handle."""
    try:
        connection.send_config_set(commands)
        return True
    except Exception as e:
        print(f"!! Command push failed: {e}")
        return False

def main():
    args = parse_arguments()
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"!! Closet '{args.closet}' not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    
    # -------------------------------------------------------------
    # PHASE 1: FAIL-FAST PRE-CHECKS (ALL IN ONE PLACE)
    # -------------------------------------------------------------
    print("-- Running network pre-flight ping checks...")
    for sw in all_devices:
        if not is_reachable(sw["host"]):
            print(f"\n!! CRITICAL ERROR: {sw['hostname']} ({sw['host']}) is offline. Aborting deployment for network safety.")
            sys.exit(1)
    print("-- Pre-checks passed! All target hardware is online.\n")
    
    # Locate our aggregation/hub switch out of the list dynamically
    local_switch = next(sw for sw in all_devices if sw["role"] == "aggregation")
    access_switches = [sw for sw in all_devices if sw["role"] == "access"]
    
    # -------------------------------------------------------------
    # PHASE 2: COMPILATION PHASE (BUILDING AND ATTACHING COMMANDS)
    # -------------------------------------------------------------
    print("-- Compiling device-specific configuration profiles...")
    hub_commands = []
    
    for sw in all_devices:
        # Populate uniform credential variables required for connection maps
        sw["device_type"] = "extreme_exos"
        sw["username"] = "admin"
        sw["password"] = "" # Left blank intentionally for Task 1 validation labs

    for sw in access_switches:
        # 1. Compile localized client edge switch profiles
        sw["compiled_commands"] = [
            f"create vlan {sw['vlan_name']}",
            f"configure vlan {sw['vlan_name']} tag {sw['vlan_id']}",
            f"configure vlan {sw['vlan_name']} add ports {sw['uplink_port']} tagged",
            f"configure vlan {sw['vlan_name']} add ports {sw['access_ports']} untagged",
            "save configuration primary"
        ]
        
        # 2. Accumulate matching aggregation trunk lines intended for Local_Switch
        hub_commands.extend([
            f"create vlan {sw['vlan_name']}",
            f"configure vlan {sw['vlan_name']} tag {sw['vlan_id']}",
            f"configure vlan {sw['vlan_name']} add ports {sw['core_trunk_port']} tagged"
        ])
        
    # Append final commit and finalize the aggregation profile
    hub_commands.append("save configuration primary")
    local_switch["compiled_commands"] = hub_commands
    
    # -------------------------------------------------------------
    # PHASE 3: UNIFIED EXECUTION PHASE (THE ULTIMATE DRY LOOP)
    # -------------------------------------------------------------
    # To maintain trunk stability, provision edge devices first, then apply trunk aggregation hubs last
    execution_order = access_switches + [local_switch]
    
    for sw in execution_order:
        print("="*50)
        print(f">> Provisioning {sw['hostname']} ({sw['host']})...")
        print(f"-- Opening SSH connection to {sw['host']}...")
        
        connection = connect_to(sw)
        if connection:
            push_success = push_commands(connection, sw["compiled_commands"])
            connection.disconnect()
            
            if push_success:
                print(f"-- Successfully deployed configuration to {sw['host']}.")
            else:
                print(f"!! CRITICAL FAULT: Push rejected on {sw['hostname']}.")
                sys.exit(1)
        else:
            print(f"!! CRITICAL FAULT: Authentication/timeout on {sw['hostname']}")
            sys.exit(1)
            
    print("\n" + "="*50)
    print("-- Success! Complete topology deployment accomplished dynamically.")

if __name__ == "__main__":
    main()
