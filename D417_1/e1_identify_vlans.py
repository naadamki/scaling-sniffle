import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="Pre-Deployment VLAN Identification Tool.")
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

def is_reachable(ip):
    """Performs a single ICMP ping check. True if online, False if offline."""
    param = "-n" if subprocess.os.name == "nt" else "-c"
    command = ["ping", param, "1", "-W", "2", ip]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def connect_to(device):
    """Establishes an SSH connection handle using Netmiko."""
    profile = {
        "device_type": "extreme_exos",
        "host": device["host"],
        "username": "admin",
        "password": "",  
    }
    try:
        return ConnectHandler(**profile)
    except NetmikoAuthenticationException:
        print(f"Authentication failed for {device['hostname']} at {device['host']}")
        return False
    except NetmikoTimeoutException:
        print(f"Timeout connecting to {device['hostname']} at {device['host']}")
        return False
    except Exception as e:
        print(f"Connection error to {device['host']}: {e}")
        return False

def main():
    args = parse_arguments()
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"!! Closet '{args.closet}' not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    
    print("-- Running network pre-flight ping checks...")
    for sw in all_devices:
        if not is_reachable(sw["host"]):
            print(f"\n!! CRITICAL ERROR: {sw['hostname']} ({sw['host']}) is offline. Aborting audit sequence.")
            sys.exit(1)
    print("-- Pre-checks passed! All target hardware is online.\n")
    
    print("="*60)
    print("TASK E1: SCANNING FOR EXISTING VLAN DATABASES")
    print("="*60)
    
    for sw in all_devices:
        print(f"\n>>> Querying VLAN architecture on: {sw['hostname']} ({sw['host']})...")
        print(f"-- Opening SSH connection to {sw['host']}...")
        
        connection = connect_to(sw)
        if connection:
            # Execute the exact operational verification command
            vlan_database_output = connection.send_command("show vlan")
            connection.disconnect()
            
            print(f"[+] Output captured from {sw['hostname']}:")
            print("-" * 50)
            print(vlan_database_output.strip())
            print("-" * 50)
        else:
            print(f"!! CRITICAL FAULT: Failed to capture memory state for {sw['hostname']}")
            sys.exit(1)
            

if __name__ == "__main__":
    main()
