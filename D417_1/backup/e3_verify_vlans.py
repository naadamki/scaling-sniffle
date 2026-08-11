import argparse
import sys
import os
import yaml
from network_manager import DeviceManager
# from network_manager import EXOSManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "")

TITLE = "network VLAN deployment verification"

def parse_arguments():
    # Handles terminal command line parameters explicitly.
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.", default="N-CoreA-01.yaml")
    p.add_argument("-c", "--closet", help="Specific closet to inspect.", default="Access_Closet_1")
    return p.parse_args()

def load_inventory(inventory, closet):
    try:
        with open(inventory, "r") as f:
            data = yaml.safe_load(f)
            try:
                return data["inventory"][closet]
            except:
                print(f"  !!  {closet} not in {inventory}")
                sys.exit(1)
    except Exception as e:
        print(f"  !!  Failed to load inventory.\n  !!  {e}")
        sys.exit(1)


def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)

    access_switches = [sw for sw in inventory if sw.get("role") == "access"]
    agg_switch = next(sw for sw in inventory if sw.get("role") == "aggregate")

    verification_summary = {}

    print(f"--  Auditing Access Switches...")
    
    for sw in access_switches:
        v_id = sw.get("vlan_id")
        v_name = sw.get("vlan_name")
        hostname = sw.get("hostname")
        
        verification_summary[hostname] = "FAILED"
        
        try:
            with DeviceManager(sw, username=ENV_USER, password=ENV_PASS) as acc:
                if acc.verify_vlan_exists(v_id, v_name):
                    verification_summary[hostname] = "PASSED"
                else:
                    print(f"  !!  CRITICAL: {hostname} is missing {v_name} ({v_id}).")
        except Exception:
            verification_summary[hostname] = "UNREACHABLE"
            print(f"  !!  Skipping {hostname} could not connect.")
            
 
    print(f"--  Auditing Aggregate Switch...")
    
    agg_hostname = agg_switch.get("hostname")
    verification_summary[agg_hostname] = "PASSED"
    
    try:
        with DeviceManager(agg_switch, username=ENV_USER, password=ENV_PASS) as agg:
            for sw in access_switches:
                v_id = sw.get("vlan_id")
                v_name = sw.get("vlan_name")
                
                if not agg.verify_vlan_exists(v_id, v_name):
                    print(f"  !!  CRITICAL: Aggregate core is missing {v_name} ({v_id}).")
                    verification_summary[agg_hostname] = "PARTIAL_FAIL"
    except Exception:
        verification_summary[agg_hostname] = "UNREACHABLE"
        print(f"  !!  CRITICAL: Could not connect to Aggregate: {agg_hostname}")

    print("FINAL VERIFICATION SUMMARY")
    
    overall_success = True
    for node, status in verification_summary.items():
        print(f"  --  Device: {node.ljust(18)} -> Audit Status: [{status}]")
        if status != "PASSED":
            overall_success = False
            
    if overall_success:
        print(f"Success! {TITLE} PASSED")
    else:
        print(f"ERROR: {TITLE} FAILED")

if __name__ == "__main__":
    main()
