import argparse
import os
from network_manager import InventoryManager, DeviceManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "network device VLAN configuration identification"

def parse_arguments():
    # Handles terminal command line parameters explicitly.
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.", default="N-CoreA-01.yaml")
    p.add_argument("-c", "--closet", help="Specific closet to inspect.", default="Access_Closet_1")
    return p.parse_args()


def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)

    for device in inventory.devices:
        hostname = (
            device.get("hostname") or device.get("host")
            if isinstance(device, dict)
            else str(device)
        )

        try:
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:
                
                vlans = connection.get_vlans(parse=True)

                print(f"--  {connection.hostname} ({connection.host}) VLAN configuration:")
                for vlan in vlans:
                    print(f"    - {vlan['name']} ({vlan['vid']})")

        except Exception as e:
            print(f"!!  Process aborted for {hostname}\n!!  {e}")

    print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()
