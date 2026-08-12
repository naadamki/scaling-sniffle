import argparse
import os
from network_manager import InventoryManager, DeviceManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "automated VLAN deployment"

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.", default="N-CoreA-01.yaml")
    p.add_argument("-c", "--closet", help="Specific closet to inspect.", default="Access_Closet_1")
    return p.parse_args()

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)
    
    vlan_map = inventory.build_required_vlan_map()

    for device in inventory.devices:
        hostname = (
            device.get("hostname") or device.get("host")
            if isinstance(device, dict)
            else str(device)
        )        
        targets_to_provision = vlan_map.get(hostname, [])

        if not targets_to_provision:
            print(f"-- Skipping {hostname}: No provisioning required.")
            continue

        try:
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
                ) as connection:

                for vlan_id, vlan_name, tagged_ports, untagged_ports in targets_to_provision:

                    if not connection.verify_vlan_exists(vlan_id=vlan_id, vlan_name=vlan_name):
                        connection.create_vlan(vlan_id, vlan_name)
                        print(f"--  {vlan_name} created on {hostname}.")
                    else:
                        print(f"--  {vlan_name} is on {hostname}.")

                    if tagged_ports and tagged_ports != "None":
                        connection.add_vlan_ports(vlan_name, tagged_ports, tag=True)

                    if untagged_ports and untagged_ports != "None":
                        connection.add_vlan_ports(vlan_name, untagged_ports, tag=False)

                connection.save_config_primary()
        except Exception as e:
            print(f"!!  Process aborted for {hostname}\n!!  {e}")

    print(f"\nSuccess running {TITLE}!\n")

if __name__ == "__main__":
    main()
