#!/usr/bin/env python3
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException,)
import configparser

switches = {
    'IT_Network': '10.10.1.21',
    'MGMT_Network': '10.10.1.22',
    'ACCT_Network': '10.10.1.23',
    'User_Network': '10.10.1.24'
}

config = configparser.ConfigParser()

for switch_name, exos_host in switches.items():
    print(f"-- Connecting to {switch_name} at {exos_host}...")
    
    device = {
        'device_type': 'extreme_exos',
        'host': exos_host,
        'port': '22',
        'username': 'admin',
        'password': '',
    }
    
    try:

        connection = ConnectHandler(**device)
        print(f"   - Connected to {switch_name} ({exos_host}) successfully.")
        
        switch_hostname = connection.send_command('show switch | grep "SysName*"')
        switch_ip = connection.send_command('show ipconfig | grep "Default*"')
        switch_config1 = connection.send_command('show config | grep "configure vl*"', read_timeout=30)
        switch_config2 = connection.send_command('show config | grep "configure sn*"', read_timeout=30)
        
        host = switch_hostname.strip()[9:35]
        ipaddress = switch_ip.strip()[8:29]
        
        print(f"   - Gathering information for host: {host.strip()}")
        print(f"     - IP Address: {ipaddress.strip()}")
        print(f"     - VLAN Configuration: {switch_config1}")
        print(f"     - SNMP Configuration: {switch_config2}")
        
        connection.disconnect()
        
        config[switch_name] = {
            'Hostname': host.strip(),
            'IP Address': ipaddress.strip(),
            'VLAN Configuration': switch_config1,
            'SNMP Configuration': switch_config2
        }
        
        print(f"   - Configuration retrieved and added to inventory for {switch_name}")
        
    except NetmikoAuthenticationException:
        print(f"   - Authentication failed for {switch_name} ({exos_host}).")
    except NetmikoTimeoutException:
        print(f"   - Timeout connecting to {switch_name} ({exos_host})")
    except Exception as e:
        print(f"   - Error connecting to {switch_name}: {str(e)}")

output_file = 'switch_inventory.ini'
try:
    with open(output_file, 'w') as configfile:
        config.write(configfile)
    print(f"-- Inventory file successfully created: {output_file}")
except Exception as e:
    print(f"-- Error writing inventory file: {str(e)}")