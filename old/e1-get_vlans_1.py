#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)

switches = {
    'IT_Network': '10.10.1.21',
    'MGMT_Network': '10.10.1.22',
    'ACCT_Network': '10.10.1.23',
    'User_Network': '10.10.1.24'
}

border = "=" * 80
print("CHECKING EXISTING VLANs ON ACCESS CLOSET 1 SWITCHES")
print(border)


for switch_name, exos_host in switches.items():
    print(f"\n[*] Connecting to {switch_name} at {exos_host}...")
    
    device = {
        'device_type': 'extreme_exos',
        'host': exos_host,
        'port': '22',
        'username': 'admin',
        'password': '',
    }
    
    try:
        connection = ConnectHandler(**device)
        print(f"[+] Successfully connected to {switch_name}")
        
        print(f"\n--- Existing VLANs on {switch_name} ({exos_host}) ---")
        vlan_output = connection.send_command('show vlan')
        print(vlan_output)
        
        connection.disconnect()
        print(f"[+] Disconnected from {switch_name}")
        
    except NetmikoAuthenticationException:
        print(f"[-] Authentication failed for {switch_name} at {exos_host}")
    except NetmikoTimeoutException:
        print(f"[-] Timeout connecting to {switch_name} at {exos_host}")
    except Exception as e:
        print(f"[-] Error connecting to {switch_name}: {str(e)}")

print(f"\n {border}")
print("VLAN CHECK COMPLETE")
print(border)