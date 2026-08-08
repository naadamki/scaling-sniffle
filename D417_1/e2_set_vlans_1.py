import argparse
import sys
import os
import yaml
from network_connection import EXOSManager

env_user = os.environ.get("EXOS_DEFAULT_USER", "admin")
env_pass = os.environ.get("EXOS_DEFAULT_PASS", "")

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
    except (yaml.YAMLError, FileNotFoundError) as e:
        print(f"!! ERROR: Loading inventory failed: {e}")
        sys.exit(1)

def main():
    args = parse_arguments()

    print("\n" + "=" * 50)    
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

    print("-" * 50)
    print(f"-- Starting Deployment for Closet: {args.closet}")

    print(f"-- Preparing Aggregate Core Switch configuration...")
    try:
        with EXOSManager(agg_switch, username=env_user, password=env_pass) as agg:
            for sw in access_switches:
                v_id = sw.get("vlan_id")
                v_name = sw.get("vlan_name")
                core_port = sw.get("core_trunk_port")
                
                if not agg.verify_vlan_exists(v_id, v_name):
                    agg.create_vlan(v_id, v_name)
                
                agg.add_vlan_ports(v_name, core_port, tag=True)
            
            agg.save_config_primary()
            
    except Exception as e:
        print(f"!! CRITICAL: Failed to provision Aggregate Core switch. Aborting run. Details: {e}")
        sys.exit(1)

    print("-" * 50)
    print("-- Transitioning to Access Switch Provisioning...")
    print("-" * 50)

    for sw in access_switches:
        v_id = sw.get("vlan_id")
        v_name = sw.get("vlan_name")
        up_port = sw.get("uplink_port")
        acc_ports = sw.get("access_ports")

        try:
            with EXOSManager(sw, username=env_user, password=env_pass) as acc:
                # 1. Verify and create the network segment locally
                if not acc.verify_vlan_exists(v_id, v_name):
                    acc.create_vlan(v_id, v_name)
                
                # 2. Tag the local physical port linking back up to the core
                acc.add_vlan_ports(v_name, up_port, tag=True)
                
                # 3. Provision local untagged desktop/router user access ports
                acc.add_vlan_ports(v_name, acc_ports, tag=False)
                
                # 4. Commit configuration to primary storage
                acc.save_config_primary()
                
        except Exception:
            print(f"!! SKIPPING: Automation failed on access switch {sw.get('hostname')} ({sw.get('host')})")
            print("-" * 50)
            continue
            
        print("-" * 50)

    print("-- Success! Complete deployment finished.")
    print("=" * 50)

if __name__ == "__main__":
    main()
