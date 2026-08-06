#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)

switches = [
    '10.10.1.21', 
    '10.10.1.22', 
    '10.10.1.23', 
    '10.10.1.24'
]

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
        print(f"    - Connected to {hostname} ({ip}) successfully.")

        vlan_config = connection.send_command('show vlan', read_timeout=30)
        print(f"      - VLAN Configuration: {vlan_config}")
        
        connection.disconnect()
        print(f"<<< Disconnected from {hostname}.")

    except NetmikoAuthenticationException:
        print(f"    - Authentication failed for {hostname} ({ip}).")
    except NetmikoTimeoutException:
        print(f"    - Timeout while connecting to {hostname} ({ip}).")
    except Exception as e:
        print(f"    - Error connecting to {hostname}: {str(e)}")


