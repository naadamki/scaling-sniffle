import argparse
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    p = argparse.ArgumentParser(description="Automated VLAN Verification Discovery Engine.")
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
    
    print("="*60)
    print("PHASE 1: SCANNING CLIENT EDGE ACCESS LAYER")
    print("="*60)
    
    for sw in access_switches:
        if not is_reachable(sw["host"]):
            print(f"[FAIL] {sw['hostname']} ({sw['host']}) is offline!")
            continue
            
        connection = connect_to(sw["host"])
        if connection:
            # Query active configuration state for this specific VLAN name from memory
            output = connection.send_command(f"show vlan {sw['vlan_name']}")
            connection.disconnect()
            
            tag_flag = f"Tag={sw['vlan_id']}"
            
            print(f"\n>>> Checking {sw['hostname']}...")
            if "VLAN NOT FOUND" in output.upper() or "ERROR" in output.upper():
                print(f"  [FAIL] Target network '{sw['vlan_name']}' does not exist on this switch.")
            elif tag_flag not in output:
                print(f"  [FAIL] Network exists but tag does not match expected ID: {sw['vlan_id']}")
            else:
                print(f"  [PASS] Verified! Network '{sw['vlan_name']}' is live with Tag {sw['vlan_id']}.")
        else:
            print(f"  [FAIL] Could not establish secure SSH session to {sw['hostname']}.")

    print("\n" + "="*60)
    print("PHASE 2: SCANNING AGGREGATION HUB (LOCAL_SWITCH)")
    print("="*60)
    
    if is_reachable(local_switch["host"]):
        connection = connect_to(local_switch["host"])
        if connection:
            print(f">>> Inspecting trunk maps on {local_switch['hostname']} ({local_switch['host']})...")
            
            for sw in access_switches:
                output = connection.send_command(f"show vlan {sw['vlan_name']}")
                
                if sw['vlan_name'] in output and f"Tag={sw['vlan_id']}" in output:
                    print(f"  [PASS] Trunk map for '{sw['vlan_name']}' (Tag {sw['vlan_id']}) is verified active.")
                else:
                    print(f"  [FAIL] Central hub missing trunk routing for network: {sw['vlan_name']}")
            connection.disconnect()
        else:
            print(f"  [FAIL] Could not establish secure SSH session to Local_Switch.")
    else:
        print(f"  [FAIL] Local_Switch ({local_switch['host']}) is offline!")

    print("\n" + "="*60)
    print("[+] Verification scan complete.")

if __name__ == "__main__":
    main()
