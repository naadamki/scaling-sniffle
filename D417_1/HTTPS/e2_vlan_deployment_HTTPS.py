import argparse
import json
import os
import sys
import yaml
from network_manager import EXOSHTTPSManager

ENV_USER = os.environ.get("EXOS_DEFAULT_USER", "admin")
ENV_PASS = os.environ.get("EXOS_DEFAULT_PASS", "")


def parse_arguments():
    # Handles parameters pushed from CLI
    p = argparse.ArgumentParser(description="Network Device VLAN Deployment.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()    


def load_devices(file_path, closet_name):
    # Load specified closet from inventory in file_path
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data["closets"][closet_name]
    except Exception as e:
        print(f"    !! Error loading inventory file '{file_path}': {e}")
        sys.exit(1)


def main():
    args = parse_arguments()
    devices = load_devices(args.inventory_file, args.closet)

    print(f"\nStarting VLAN deployment for closet '{args.closet}'...")


    acc_switches = [sw for sw in devices if sw.get("role") == "access"]
    
    try:
        agg_switch = next(sw for sw in devices if sw.get("role") == "aggregate")
    except StopIteration:
        print("    !! Error: No aggregate switch found in this closet's inventory.")
        sys.exit(1)

    print(f"Preparing Aggregate Switch Configuration...")

    try:
        with EXOSHTTPSManager(agg_switch, username=ENV_USER, password=ENV_PASS) as agg:
            for sw in acc_switches:
                vlan_id = sw.get("vlan_id")
                vlan_name = sw.get("vlan_name")
                core_port = sw.get("core_trunk_port")

                if not agg.verify_vlan_exists(vlan_id, vlan_name):
                    agg.create_vlan(vlan_id, vlan_name)

                agg.add_vlan_ports(vlan_name, core_port, tag=True)

            agg.save_config_primary()

    except Exception as e:
        print(f"    !! Failed to provision Aggregate Switch. Aborting.\n{e}")
        sys.exit(1)

    print(f"Deploying access switch provisioning...")

    for sw in acc_switches:
        vlan_id = sw.get("vlan_id")
        vlan_name = sw.get("vlan_name")
        up_port = sw.get("uplink_port")
        acc_ports = sw.get("access_ports")

        try:
            with EXOSHTTPSManager(sw, username=ENV_USER, password=ENV_PASS) as acc:
                if not acc.verify_vlan_exists(vlan_id, vlan_name):
                    acc.create_vlan(vlan_id, vlan_name)
                
                acc.add_vlan_ports(vlan_name, up_port, tag=True)                
                acc.add_vlan_ports(vlan_name, acc_ports, tag=False)
                acc.save_config_primary()
                
        except Exception as e:
            print(f"    !! Deployment failed on {sw.get('hostname')} ({sw.get('host')}): {e}")
            continue

    print("Success! Complete deployment finished.")
    print("\n")

if __name__ == "__main__":
    main()