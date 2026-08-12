import argparse
import os
from network_manager import InventoryManager, DeviceManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "network VLAN deployment verification"

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
        required_vlans = vlan_map.get(hostname, [])
        
        if not required_vlans:
            print(f"--  Skipping {hostname}: No required VLAN mappings found.")
            continue
            
        try:
            with DeviceManager(
                device, username=ENV_USER, password=ENV_PASS
            ) as connection:

                current_vlans = connection.get_vlans(parse=True)

                current_vlan_set = {(str(vlan.get("vid")), vlan.get("name")) for vlan in current_vlans}

                verification_results = []
                for required_vlan in required_vlans:
                    vlan_id, vlan_name, _, _ = required_vlan
                    
                    target_tuple = (str(vlan_id), vlan_name)
                    is_present = target_tuple in current_vlan_set
                    
                    verification_results.append({
                        "vlan_id": vlan_id,
                        "vlan_name": vlan_name,
                        "verified": is_present
                    })

                print(f"--  Verification Report for {connection.hostname} ({connection.host}):")
                device_healthy = True
                
                for result in verification_results:
                    if result["verified"]:
                        print(f"    - PASS: VLAN {result['vlan_name']} (ID: {result['vlan_id']}) is active.")
                    else:
                        print(f"    - FAIL: VLAN {result['vlan_name']} (ID: {result['vlan_id']}) is MISSING.")
                        device_healthy = False

                if device_healthy:
                    print(f"    Status: All required VLANs verified successfully.")
                else:
                    print(f"    Status: Warning - Mismatched VLAN state detected.")
                
        except Exception as e:
            print(f"!!  Process aborted for {hostname}\n!!  {e}")

    print(f"\nSuccess running {TITLE}!\n")

if __name__ == "__main__":
    main()