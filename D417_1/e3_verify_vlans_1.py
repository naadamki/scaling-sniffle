import argparse
import sys
import os
import yaml
from network_manager import EXOSManager

env_user = os.environ.get("EXOS_DEFAULT_USER", "admin")
env_pass = os.environ.get("EXOS_DEFAULT_PASS", "")

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="VLAN Verification Engine")
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

def main():
    args = parse_arguments()
    print(f"-- Retrieving inventory file '{args.inventory_file}'...")
    devices = load_inventory(args.inventory_file)
    
    if args.closet not in devices["closets"]:
        print(f"!! ERROR: {args.closet} not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    access_switches = [sw for sw in all_devices if sw.get("role") == "access"]
    
    try:
        agg_switch = next(sw for sw in all_devices if sw.get("role") == "aggregate")
    except StopIteration:
        print("!! ERROR: No aggregate switch found in inventory file.")
        sys.exit(1)

    # Dictionary to keep score for a professional summary at the end
    verification_summary = {}

    print("\n" + "=" * 50)
    print(f"-- Starting VLAN Verification for {args.closet}")
    print("-" * 50)

    print("-- Auditing Access Switches...")
    print("-" * 50)
    
    for sw in access_switches:
        v_id = sw.get("vlan_id")
        v_name = sw.get("vlan_name")
        hostname = sw.get("hostname")
        
        verification_summary[hostname] = "FAILED"
        
        try:
            with EXOSManager(sw, username=env_user, password=env_pass) as acc:
                if acc.verify_vlan_exists(v_id, v_name):
                    verification_summary[hostname] = "PASSED"
                else:
                    print(f"!! CRITICAL: {hostname} is missing {v_name} ({v_id}).")
        except Exception:
            verification_summary[hostname] = "UNREACHABLE"
            print(f"!! SKIPPING: Could not connect to {hostname}.")
            
        print("-" * 50)

    print("\n-- Auditing Aggregate Switch...")
    print("-" * 50)
    
    agg_hostname = agg_switch.get("hostname")
    verification_summary[agg_hostname] = "PASSED"
    
    try:
        with EXOSManager(agg_switch, username=env_user, password=env_pass) as agg:
            for sw in access_switches:
                v_id = sw.get("vlan_id")
                v_name = sw.get("vlan_name")
                
                if not agg.verify_vlan_exists(v_id, v_name):
                    print(f"!! CRITICAL: Aggregate core is missing {v_name} ({v_id}).")
                    verification_summary[agg_hostname] = "PARTIAL_FAIL"
    except Exception:
        verification_summary[agg_hostname] = "UNREACHABLE"
        print(f"!! CRITICAL: Could not connect to Aggregate: {agg_hostname}")

    print("\n" + "-" * 50)
    print("FINAL VERIFICATION SUMMARY")
    print("-" * 50)
    
    overall_success = True
    for node, status in verification_summary.items():
        print(f"Device: {node.ljust(18)} -> Audit Status: [{status}]")
        if status != "PASSED":
            overall_success = False
            
    print("-" * 50)
    if overall_success:
        print("-- SUCCESS: Entire network topology matches YAML intent!")
    else:
        print("!! ALERT: Audit identified missing required VLAN configuration.")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
