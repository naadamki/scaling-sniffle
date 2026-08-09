from netmiko import ConnectHandler

# List all switch IP addresses
switches = [
    "10.10.1.20",
    "10.10.1.21",
    "10.10.1.22",
    "10.10.1.23",
    "10.10.1.24"
]

NEW_ADMIN_PASS = "1234"

for ip in switches:
    device = {
        'device_type': 'extreme_exos',
        'host': ip,
        'username': 'admin',
        'password': '',  # Netmiko handles empty strings correctly
        'disabled_algorithms': dict(pubkeys=['rsa-sha2-256', 'rsa-sha2-512'])
    }
    
    print(f"[*] Bootstrapping initial password on {ip}...")
    try:
        net_connect = ConnectHandler(**device)
        
        # EXOS prompts for password twice when running 'configure account admin password'
        net_connect.send_command("configure account admin password", expect_string=r"New password:")
        net_connect.send_command(NEW_ADMIN_PASS, expect_string=r"Re-enter password:")
        net_connect.send_command(NEW_ADMIN_PASS)
        
        # Save configuration and handle the (y/N) confirmation prompt
        net_connect.send_command("save configuration primary", expect_string=r"\(y/N\)")
        net_connect.send_command("y")
        
        net_connect.disconnect()
        print(f"[+] Successfully bootstrapped {ip}")
    except Exception as e:
        print(f"[-] Failed to bootstrap {ip}: {e}")