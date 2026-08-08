import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="VLAN Identification")
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
        print(f"!! ERROR: {device['hostname']} ({device['host']}) failed authentication.")
        return False
    except NetmikoTimeoutException:
        print(f"!! ERROR: {device['hostname']} ({device['host']}) connection timed out.")
        return False
    except Exception as e:
        print(f"!! ERROR: {device['hostname']} ({device['host']}): {e}")
        return False

def main():
    args = parse_arguments()

    print(f">> Retrieving inventory file '{file_path}...")    
    devices = load_inventory(args.inventory_file)
    if args.closet not in devices["closets"]:
        print(f"!! ERROR: {args.closet} not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    
    print("-- Running network device availability checks...")
    if not all(is_reachable(sw["host"]) for sw in all_devices):
        print(f"!! Error: {sw["host"]} is offline. Aborting.")
        sys.exit(1)
    else:
        print("-- Availability checks passed! All target network devices are online.\n")
    

    
    for sw in all_devices:
        print("="*50)
        print(f">> Connecting to {sw['host']}...")        
        connection = connect_to(sw)
        if connection:
            print(f"-- Connected to {sw['host']}.")
            print(f"-- Retrieving VLAN configuration for {sw['host']}...")
            vlan_database_output = connection.send_command("show vlan")
            print(f"<< Disonnecting from {sw['host']}.")
            connection.disconnect()
            
            print(f"-- {sw['hostname']} VLAN configuration:")
            print(vlan_database_output.strip())
            print("-" * 50)
        else:
            print(f"!! ERROR: unable to connect to {sw['host']}. Aborting.")
            sys.exit(1)

    print("\n" + "="*50)
    print("-- Success! VLAN configuration retrieval complete.")
            

if __name__ == "__main__":
    main()
