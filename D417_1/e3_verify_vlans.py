import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="VLAN Verification")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to verify.")
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

def connect_to(ip_address, hostname="Switch"):
    """Establishes an SSH connection handle using Netmiko."""
    profile = {
        "device_type": "extreme_exos",
        "host": ip_address,
        "username": "admin",
        "password": "",
    }
    try:
        return ConnectHandler(**profile)
    except NetmikoAuthenticationException:
        print(f"!! ERROR: {hostname} ({ip_address}) failed authentication.")
    except NetmikoTimeoutException:
        print(f"!! ERROR: {hostname} ({ip_address}) connection timed out.")
    except Exception as e:
        print(f"!! ERROR: {hostname} ({ip_address}): {e}")
    return False

def verify_vlan_presence(vlan_output, sw_target, context_label="Switch"):
    """Parses raw text data to verify name and VID presence."""
    name_exists = sw_target['vlan_name'] in vlan_output
    vid_exists = str(sw_target['vlan_id']) in vlan_output
    
    if not name_exists:
        print(f"FAIL - [{context_label}] Target network '{sw_target['vlan_name']}' was not found.")
        return False
    elif not vid_exists:
        print(f"FAIL - [{context_label}] '{sw_target['vlan_name']}' matches, but expected VID ({sw_target['vlan_id']}) is missing.")
        return False
    else:
        print(f"PASS - [{context_label}] Verified! Network '{sw_target['vlan_name']}' is live with VID {sw_target['vlan_id']}.")
        return True

def main():
    args = parse_arguments()

    print(f">> Retrieving inventory file '{file_path}...")    
    devices = load_inventory(args.inventory_file)
    if args.closet not in devices["closets"]:
        print(f"!! ERROR: {args.closet} not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    access_switches = [sw for sw in all_devices if sw["role"] == "access"]
    agg_switch = next(sw for sw in all_devices if sw["role"] == "aggregate")

    print("-- Running network device availability checks...")
    if not all(is_reachable(sw["host"]) for sw in all_devices):
        print(f"!! Error: {sw["host"]} is offline. Aborting.")
        sys.exit(1)
    else:
        print("-- Availability checks passed! All target network devices are online.\n")

    
    for sw in access_switches:
        print("="*50)
        print(f">> Connecting to {sw['host']}...")
        connection = connect_to(sw["host"], sw["hostname"])
        
        if connection:
            print(f"-- Connected to {sw['hostname']} ({sw['host']}).")
            print(f"-- Retrieving VLAN configuration from {sw['hostname']} ({sw['host']})...")
            output = connection.send_command("show vlan")
            print(f"<< Disconnecting from {sw['host']}...")
            connection.disconnect()
            print(f"-- Verifying VLAN configuration...")
            verify_vlan_presence(output, sw, context_label="Local")
            

    
    connection = connect_to(agg_switch["host"], agg_switch["hostname"])
    if connection:
        print(f"Connected to {agg_switch['hostname']} ({agg_switch['host']}).")
        print(f"-- Retrieving VLAN configuration from {agg_switch['hostname']} ({agg_switch['host']})...")        
        output = connection.send_command("show vlan")
        print(f"<< Disconnecting from {agg_switch['hostname']}...")        
        connection.disconnect()
        
        for sw in access_switches:
            print(f"-- Verifying VLAN configuration...")
            verify_vlan_presence(output, sw, context_label="Trunk Map")
            
    print("\n" + "="*50)
    print("-- Success! VLAN deployment verification complete.")


if __name__ == "__main__":
    main()
