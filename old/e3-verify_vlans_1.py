#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)

switches = {
    'IT_Network': '10.10.1.21',
    'MGMT_Network': '10.10.1.22',
    'ACCT_Network': '10.10.1.23',
    'User_Network': '10.10.1.24'
}

vlans_to_verify = {
    '10': 'IT_Network',
    '20': 'MGMT_Network',
    '30': 'ACCT_Network',
    '40': 'User_Network'
}

border = "=" * 80
print("VERIFYING VLAN CONFIGURATION ON ACCESS CLOSET 1 SWITCHES")
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
        
        print(f"\n--- VLAN Verification for {switch_name} ({exos_host}) ---")
        vlan_output = connection.send_command('show vlan')
        print(vlan_output)
        
        print(f"\n--- Verifying Required VLANs on {switch_name} ---")
        vlan_names = vlan_output.lower()
        
        all_present = True
        for vlan_id, vlan_name in vlans_to_verify.items():
            if vlan_name.lower() in vlan_names or f'vlan {vlan_id}' in vlan_names:
                print(f"[+] VLAN {vlan_id} ({vlan_name}) - VERIFIED")
            else:
                print(f"[-] VLAN {vlan_id} ({vlan_name}) - NOT FOUND")
                all_present = False
        
        if all_present:
            print(f"\n[+] All required VLANs are present on {switch_name}")
        else:
            print(f"\n[-] Some VLANs are missing on {switch_name}")
        
        connection.disconnect()
        print(f"[+] Disconnected from {switch_name}")
        
    except NetmikoAuthenticationException:
        print(f"[-] Authentication failed for {switch_name} at {exos_host}")
    except NetmikoTimeoutException:
        print(f"[-] Timeout connecting to {switch_name} at {exos_host}")
    except Exception as e:
        print(f"[-] Error connecting to {switch_name}: {str(e)}")

print(f"\n + {border}")
print("VLAN VERIFICATION COMPLETE")
print(border)