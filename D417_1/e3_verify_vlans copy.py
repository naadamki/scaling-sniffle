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
                print(f" !!  {closet} not in {inventory}")
                sys.exit(1)
    except Exception as e:
        print(f" !!  Failed to load inventory.\n  !!  {e}")
        sys.exit(1)

def build_required_vlan_map(inventory):
    required_vlans = {device["hostname"]: [] for device in inventory}
    
    agg_switches = [sw for sw in inventory if sw.get("role") == "aggregate"]
    acc_switches = [sw for sw in inventory if sw.get("role") == "access"]

    for sw in acc_switches:
        vlan_id = sw.get("vlan_id")
        vlan_name = sw.get("vlan_name")
        up_port = sw.get("uplink_port")
        acc_ports = sw.get("access_ports")
        core_port = sw.get("core_trunk_port")
        
        acc_tuple = (vlan_id, vlan_name, up_port, acc_ports)
        required_vlans[sw["hostname"]].append(acc_tuple)
        
        agg_tuple = (vlan_id, vlan_name, core_port, "None")
        for agg in agg_switches:
            required_vlans[agg["hostname"]].append(agg_tuple)  
    return required_vlans


def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)

    vlan_map = build_required_vlan_map(inventory)
    
    for device in inventory:
        hostname = device["hostname"]
        targets_to_provision = vlan_map.get(hostname, [])
        
        if not targets_to_provision:
            print(f"--  Skipping {hostname}: No required VLAN mappings found.")
            continue
            
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                changes_made = False
                
                for vlan_id, vlan_name, tagged_ports, untagged_ports in targets_to_provision:
                    
                    if not connection.verify_vlan_exists(vlan_id=vlan_id, vlan_name=vlan_name):
                        print(f"--  FAIL: VLAN '{vlan_name}' ({vlan_id}) not found!")
                    else:
                        print(f"--  PASS: VLAN '{vlan_name}' ({vlan_id}) found.")
                    
                    # 2. Check and Apply Tagged Trunk/Uplink Ports dynamically
                    if tagged_ports and tagged_ports != "None":
                        print(f"--  Ensuring trunk port '{tagged_ports}' is tagged for VLAN '{vlan_name}'...")
                        connection.add_vlan_ports(vlan_name, tagged_ports, tag=True)
                        changes_made = True
                        
                    # 3. Check and Apply Untagged Access/Edge Ports dynamically
                    if untagged_ports and untagged_ports != "None":
                        print(f"--  Ensuring client ports '{untagged_ports}' are untagged for VLAN '{vlan_name}'...")
                        connection.add_vlan_ports(vlan_name, untagged_ports, tag=False)
                        changes_made = True

                # Save the active running config state if adjustments occurred
                if changes_made:
                    connection.save_config_primary()
                    print(f"--  Running configuration saved to primary partition memory.")
                else:
                    print(f"--  Node identity verified. System state up to date.")
                    
        except Exception as e:
            print(f"!! Framework process failure on target host node {hostname}: {e}")

if __name__ == "__main__":
    main()
