import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    p = argparse.ArgumentParser(description="Task E: Automated VLAN Verification Discovery Engine.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to verify.")
    return p.parse_args()

def load_inventory(file_path):
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
    param = "-n" if subprocess.os.name == "nt" else "-c"
    command = ["ping", param, "1", "-W", "2", ip]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def connect_to(device_ip):
    profile = {
        "device_type": "extreme_exos",
        "host": device_ip,
        "username": "admin",
        "password": "",
    }
    try:
        return ConnectHandler(**profile)
    except Exception:
        return False

def main():
    args = parse_arguments()
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"!! Closet '{args.closet}' not found.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    access_switches = [sw for sw in all_devices if sw["role"] == "access"]
    local_switch = next(sw for sw in all_devices if sw["role"] == "aggregation")
    
    print("[*] Launching Post-Deployment VLAN Verification Scan...\n")
    
    # -------------------------------------------------------------
    # PHASE 1: SCANNING CLIENT EDGE ACCESS LAYER
    # -------------------------------------------------------------
    print("="*60)
    print("PHASE 1: SCANNING CLIENT EDGE ACCESS LAYER")
    print("="*60)
    
    for sw in access_switches:
        if not is_reachable(sw["host"]):
            print(f"[FAIL] {sw['hostname']} ({sw['host']}) is offline!")
            continue
            
        connection = connect_to(sw["host"])
        if connection:
            # Query the broad VLAN database overview table
            output = connection.send_command("show vlan")
            connection.disconnect()
            
            print(f"\n>>> Checking {sw['hostname']}...")
            
            # FIXED: EXOS prints the VLAN Name and the VID on the same line in 'show vlan'
            # We look for the custom VLAN name and the numerical ID string inside the output table
            vlan_name_exists = sw['vlan_name'] in output
            vid_string_exists = str(sw['vlan_id']) in output
            
            if not vlan_name_exists:
                print(f"  [FAIL] Target network '{sw['vlan_name']}' was not found on this switch.")
            elif not vid_string_exists:
                print(f"  [FAIL] Network name matches, but expected VID ({sw['vlan_id']}) is missing.")
            else:
                print(f"  [PASS] Verified! Network '{sw['vlan_name']}' is live with VID {sw['vlan_id']}.")
        else:
            print(f"  [FAIL] Could not establish secure SSH session to {sw['hostname']}.")

    # -------------------------------------------------------------
    # PHASE 2: SCANNING AGGREGATION HUB (LOCAL_SWITCH)
    # -------------------------------------------------------------
    print("\n" + "="*60)
    print("PHASE 2: SCANNING AGGREGATION HUB (LOCAL_SWITCH)")
    print("="*60)
    
    if is_reachable(local_switch["host"]):
        connection = connect_to(local_switch["host"])
        if connection:
            print(f">>> Inspecting trunk maps on {local_switch['hostname']} ({local_switch['host']})...\n")
            
            # FIXED: Pull the full 'show vlan' database from the hub to check all networks at once
            hub_output = connection.send_command("show vlan")
            connection.disconnect()
            
            for sw in access_switches:
                # Check if the specific access switch's network and ID exist on the hub switch
                if sw['vlan_name'] in hub_output and str(sw['vlan_id']) in hub_output:
                    print(f"  [PASS] Trunk map for '{sw['vlan_name']}' (VID {sw['vlan_id']}) is verified active.")
                else:
                    print(f"  [FAIL] Central hub missing trunk routing for network: {sw['vlan_name']}")
        else:
            print(f"  [FAIL] Could not establish secure SSH session to Local_Switch.")
    else:
        print(f"  [FAIL] Local_Switch ({local_switch['host']}) is offline!")

    print("\n" + "="*60)
    print("[+] Verification scan complete.")

if __name__ == "__main__":
    main()
