import os
import yaml
from netmiko import ConnectHandler

# Load inventory
with open("hosts.yaml", "r") as f:
    inventory = yaml.safe_load(f)

hosts = inventory['all']['children']['Access_Closet_1']['hosts']

# Read your local public key content
pub_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
with open(pub_key_path, "r") as kf:
    pub_key_data = kf.read().strip()

for name, data in hosts.items():
    ip = data['ansible_host']
    print(f"Configuring SSH keys on {name} ({ip})...")
    
    try:
        # Connect with Netmiko using the blank password
        conn = ConnectHandler(
            device_type="extreme_exos",
            host=ip,
            username="admin",
            password="",
            disabled_algorithms=dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
        )
        
        # 1. Enable SSH2
        conn.send_config_set(["enable ssh2"], cmd_verify=False)
        
        # 2. Save public key directly to the switch file system via SFTP/SCP method or file write
        # Alternatively, EXOS allows writing the key via config or writing a file. 
        # Since you used SCP, we can push it or use EXOS command to add the key string directly:
        # Exos command syntax for adding a public key string directly:
        # configure sshd2 user-key <key-name> add user admin ... wait, let's write it to a file on the switch first.
        
        # Actually, Netmiko has a built-id transfer function, or we can use EXOS command if it supports text-based key import.
        # Let's use the file transfer protocol or write it via a temporary file:
        
        # Let's write the public key content to a file on the switch using SFTP
        remote_filename = "id_rsa.pub"
        conn.write_scp_file(pub_key_path, remote_filename=remote_filename)
        
        # 3. Register the key to the admin user
        conn.send_config_set([
            f"configure sshd2 user-key {remote_filename} add user admin"
        ], cmd_verify=False)
        
        # 4. Save configuration
        save_out = conn.send_command_timing("save configuration primary")
        if "(y/n)" in save_out.lower() or "?" in save_out or "save configuration to" in save_out.lower():
            conn.send_command_timing("y")
            
        conn.disconnect()
        print(f"  -> Success! SSH key deployed to {name}.")
        
    except Exception as e:
        print(f"  -> Failed on {ip}: {e}")