#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)

switches = {
    'IT_Network': '10.10.1.21',
    'MGMT_Network': '10.10.1.22',
    'ACCT_Network': '10.10.1.23',
    'User_Network': '10.10.1.24'
}

vlans_to_create = {
    '10': 'IT_Network',
    '20': 'MGMT_Network',
    '30': 'ACCT_Network',
    '40': 'User_Network'
}

border = "=" * 80
print("DEPLOYING VLAN INFRASTRUCTURE TO ACCESS CLOSET 1 SWITCHES")
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
        
        print(f"\n--- Creating VLANs on {switch_name} ({exos_host}) ---")
        
        for vlan_id, vlan_name in vlans_to_create.items():
            try:
                create_command = f'create vlan {vlan_name} tag {vlan_id}'
                print(f"[*] Executing: {create_command}")
                output = connection.send_command(create_command)
                print(f"[+] VLAN {vlan_id} ({vlan_name}) created successfully")
                print(f"    Output: {output}")
                
            except Exception as e:
                print(f"[-] Error creating VLAN {vlan_id} ({vlan_name}): {str(e)}")
        
        print(f"\n[*] Saving configuration on {switch_name}...")
        save_output = connection.send_command('save config')
        print(f"[+] Configuration saved")
        
        connection.disconnect()
        print(f"[+] Disconnected from {switch_name}")
        
    except NetmikoAuthenticationException:
        print(f"[-] Authentication failed for {switch_name} at {exos_host}")
    except NetmikoTimeoutException:
        print(f"[-] Timeout connecting to {switch_name} at {exos_host}")
    except Exception as e:
        print(f"[-] Error connecting to {switch_name}: {str(e)}")

print(f"\n {border}")
print("VLAN DEPLOYMENT COMPLETE")
print(border)