import argparse
import sys
import os
import yaml
from network_manager import DeviceManager
# from network_manager import EXOSManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "")

TITLE = "automated VLAN depoyment"

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
        print(f"  !!  Failed to load inventory.")
        print(f"  !!  {e}")
        sys.exit(1)


def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
            
    acc_switches = [sw for sw in inventory if sw.get("role") == "access"]
    agg_switch = next(sw for sw in inventory if sw.get("role") == "aggregate")

    print(f"--  Deploying VLAN configuration to aggregation ({agg_swith["hostname"]})...")
    try:
        with DeviceManager(agg_switch, username=ENV_USER, password=ENV_PASS) as agg:
            for sw in acc_switches:
                v_id = sw.get("vlan_id")
                v_name = sw.get("vlan_name")
                core_port = sw.get("core_trunk_port")
                
                if not agg.verify_vlan_exists(v_id, v_name):
                    agg.create_vlan(v_id, v_name)
                
                agg.add_vlan_ports(v_name, core_port, tag=True)
            
            agg.save_config_primary()
            
    except Exception as e:
        print(f"  !!  Failed to provision Aggregate Core switch. Aborting.\n  !!  {e}")
        sys.exit(1)

    print("--  Deploying access switch provisioning...")

    for sw in acc_switches:
        v_id = sw.get("vlan_id")
        v_name = sw.get("vlan_name")
        up_port = sw.get("uplink_port")
        acc_ports = sw.get("access_ports")

        try:
            with DeviceManager(sw, username=ENV_USER, password=ENV_PASS) as acc:
                if not acc.verify_vlan_exists(v_id, v_name):
                    acc.create_vlan(v_id, v_name)
                
                acc.add_vlan_ports(v_name, up_port, tag=True)                
                acc.add_vlan_ports(v_name, acc_ports, tag=False)
                acc.save_config_primary()
                
        except Exception as e:
            print(f"  !!  Failed to provision access switch. Aborting.\n  !!  {e}")

print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()

