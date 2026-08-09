import yaml
from netmiko import ConnectHandler

with open("hosts.yaml", "r") as f:
    inventory = yaml.safe_load(f)

hosts = inventory['all']['children']['Access_Closet_1']['hosts']

new_admin_password = "1234"

print("Starting Admin Password Bootstrap")

for name, data in hosts.items():
    ip = data['ansible_host']
    print(f"\nConnecting to {name} ({ip})...")
    
    try:
        conn = ConnectHandler(
            device_type="extreme_exos",
            host=ip,
            username="admin",
            password="",
            disabled_algorithms=dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        )
        
        print(f"    -- Connected successfully. Updating admin password...")
        conn.send_config_set([f"configure account admin password {new_admin_password}"], cmd_verify=False)
        
        print(f"    -- Saving configuration to primary...")
        save_out = conn.send_command_timing("save configuration primary")
        
        if "(y/n)" in save_out.lower() or "?" in save_out or "overwrite" in save_out.lower():
            conn.send_command_timing("y")
            
        conn.disconnect()
        print(f"    -- SUCCESS {name} updated and configuration saved.")
        
    except Exception as e:
        print(f"    !! ERROR Failed to configure {name}: {e}")

print("Bootstrap Complete. Ready for Day 1.")
