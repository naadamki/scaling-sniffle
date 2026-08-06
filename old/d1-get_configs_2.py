#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)
import configparser

switches = [
    '10.10.1.21', 
    '10.10.1.22', 
    '10.10.1.23', 
    '10.10.1.24'
]

config = configparser.ConfigParser()
output_file = 'd1-inventory.ini'

for ip in switches:    
    device = {
        'device_type': 'extreme_exos',
        'host': ip,
        'port': '22',
        'username': 'admin',
        'password': '',
    }

    print(f">>> Connecting to {ip}...")    
    try:
        connection = ConnectHandler(**device)

        hostname = connection.find_prompt().strip(" #>").strip()
        print(f"- Connected to {hostname} ({ip}) successfully.")

        config_output = connection.send_command('show config')
        print(f"- Configuration information for {hostname} ({ip}):\n")        
        print(f"  - {config_output}")
        
        
        config[hostname] = {
            'Hostname': hostname,
            'IP Address': ip,
            'Configuration': config_output,
        }        
        print(f"- Configuration for {hostname} retrieved and added to {output_file}.")

        connection.disconnect()
        print(f"<<< Disconnected from {hostname}.")


    except NetmikoAuthenticationException:
        print(f"- Authentication failed for {hostname} ({ip}).")
    except NetmikoTimeoutException:
        print(f"- Timeout while connecting to {hostname} ({ip}).")
    except Exception as e:
        print(f"- Error connecting to {hostname}: {str(e)}")


try:
    with open(output_file, 'w') as configfile:
        config.write(configfile)
    print(f"--- Inventory file successfully created: {output_file}")
except Exception as e:
    print(f"--- Error writing inventory file: {str(e)}")