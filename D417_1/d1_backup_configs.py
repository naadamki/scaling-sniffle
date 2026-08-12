import argparse
import configparser
import os
from network_manager import DeviceManager, InventoryManager

ENV_USER = os.environ.get("SVC_USER", "netsvc")
ENV_PASS = os.environ.get("SVC_PASS", "SVC123")

TITLE = "network device configuration backup"


def parse_arguments():
    # Handles terminal command line parameters explicitly.
    p = argparse.ArgumentParser(description=f"Script for {TITLE}.")
    p.add_argument("-i", "--inventory", help="Building Block YAML inventory file.",
        default="N-CoreA-01.yaml",
    )
    p.add_argument("-c", "--closet", help="Specific closet to inspect.",
        default="Access_Closet_1",
    )
    return p.parse_args()

def main():
    print(f"\nStarting {TITLE}...")

    args = parse_arguments()
    inventory = InventoryManager(args.inventory, args.closet)

    output_file = "d1_backup_configs_output.ini"
    config = configparser.ConfigParser()

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
                configuration_output = connection.get_config()
                if configuration_output:
                    config[connection.hostname] = {
                        "Hostname": connection.hostname,
                        "IP Address": connection.host,
                        "Configuration": configuration_output,
                    }
                    print(f"--  {hostname} configuration backup created.")
                else:
                    print(f"!!  Failed to get configuration for {hostname}")

        except Exception as e:
            print(f"!!  Process aborted for {hostname}\n!!  {e}")

    print(f"--  Appending aggregated device backups to {output_file}...")
    with open(output_file, "w") as f:
        config.write(f)

    print(f"Success running {TITLE}!\n")


if __name__ == "__main__":
    main()