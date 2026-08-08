import argparse
import configparser
import subprocess
import sys
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

def parse_arguments():
    """Handles terminal command line parameters explicitly."""
    p = argparse.ArgumentParser(description="Network Device Configuration Backups.")
    p.add_argument("inventory_file", help="Path to the building YAML inventory file.")
    p.add_argument("closet", help="Specific closet grouping to inspect.")
    return p.parse_args()

def load_inventory(file_path):
    """Safely opens and reads the YAML architecture file."""
    try:
        with open(file_path, "r") as file:    
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(f"!! YAML parsing error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"!! '{file_path}' not found.")
        sys.exit(1)

def is_reachable(ip):
    """Performs a single ICMP ping check. True if online, False if offline."""
    param = "-n" if subprocess.os.name == "nt" else "-c"
    command = ["ping", param, "1", "-W", "2", ip]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def connect_to(device_ip):
    """Establishes an SSH connection handle using Netmiko."""
    profile = {
        "device_type": "extreme_exos",
        "host": device_ip,
        "username": "admin",
        "password": "",
        }
    try:
        return ConnectHandler(**profile)
    except NetmikoAuthenticationException:
        print(f"!! ERROR: Authentication failed for switch at {device_ip}")
        return False
    except NetmikoTimeoutException:
        print(f"!! ERROR: Timeout connecting to switch at {device_ip}")
        return False
    except Exception as e:
        print(f"!! ERROR: Connection error to {device_ip}: {e}")
        return False

def main():
    args = parse_arguments()

    print(f">> Retrieving inventory file '{file_path}...")    
    devices = load_inventory(args.inventory_file)
    if args.closet not in devices["closets"]:
        print(f"!! ERROR: '{args.closet}' not found in {args.inventory_file}.")
        sys.exit(1)
        
    all_devices = devices["closets"][args.closet]
    output_filename = "d1_get_configs.ini"
    
    config = configparser.ConfigParser()
    
    print("-- Running network device availability checks...")
    if not all(is_reachable(sw["host"]) for sw in all_devices):
        print(f"!! Error: {sw["host"]} is offline. Aborting.")
        sys.exit(1)
    else:
        print("-- Availability checks passed! All target network devices are online.\n")

    
    for sw in all_devices:
        print("="*50)
        print(f">> Connecting to {sw['host']}...")
        connection = connect_to(sw["host"])
        if connection:
            switch_hostname = connection.send_command('show switch | grep "SysName*"')
            switch_ip = connection.send_command('show ipconfig | grep "Default*"')
            switch_config1 = connection.send_command('show config | grep "configure vl*"', read_timeout=30)
            switch_config2 = connection.send_command('show config | grep "configure sn*"', read_timeout=30)
            connection.disconnect()
            
            host_parsed = switch_hostname.strip()[9:35].strip()
            ip_parsed = switch_ip.strip()[8:29].strip()
            
            print(f"-- Found Host: {host_parsed}")
            print(f"-- Found IP: {ip_parsed}")
            
            config[host_parsed] = {
                'Hostname': host_parsed,
                'IP Address': ip_parsed,
                'VLAN Configuration': switch_config1,
                'SNMP Configuration': switch_config2
            }
            print(f"-- Profile parsed successfully for {host_parsed}.")
        else:
            print(f"!! ERROR: unable to connect to {sw['host']}. Aborting.")
            sys.exit(1)
            
    print("\n" + "="*50)
    print(f"-- Appending aggregated data to {output_filename}...")
    
    with open(output_filename, 'w') as configfile:
        config.write(configfile)
        
    print(f"-- {output_filename} complete.")

    print("\n" + "="*50)
    print("-- Success! Device configuration retrieval complete.")


if __name__ == "__main__":
    main()
