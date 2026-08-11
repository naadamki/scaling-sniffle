import argparse
import configparser
import sys
import os
import yaml
from network_manager import DeviceManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "")

TITLE = "network device configuration backup"

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
                print(f"!!  {closet} not in {inventory}")
                sys.exit(1)
    except Exception as e:
        print(f"!!  Failed to load inventory.")
        print(f"!!  {e}")
        sys.exit(1)

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = load_inventory(args.inventory, args.closet)
    output_file = "d1_backup_configs_output.ini"
    config = configparser.ConfigParser()
 
    for device in inventory:
        device_label = device.get("hostname") or device.get("host") if isinstance(device, dict) else str(device)
        try:
            with DeviceManager(device, username=ENV_USER, password=ENV_PASS) as connection:
                output = connection.get_config()
                if output:
                    config[connection.hostname] = {
                        'Hostname': connection.hostname,
                        'IP Address': connection.host,
                        'Configuration': output
                    }
                    print(f"--  {device_label} configuration backup created.")
                else:
                    print(f"!!  Failed to get configuration for {device_label}")                

        except Exception as e:
            print(f"!!  Process aborted for {device_label}\n!!  {e}")
            
            
    print(f"--  Appending aggregated device backups to {output_file}...")
    with open(output_file, 'w') as f:
        config.write(f)

print(f"Success running {TITLE}!\n")

if __name__ == "__main__":
    main()


