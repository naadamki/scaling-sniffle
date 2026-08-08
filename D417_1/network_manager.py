import sys
from netmiko import ConnectHandler

class EXOSManager:
    def __init__(self, device_params, username=None, password=None):
        self.device_params = device_params.copy()
        if username and "username" not in self.device_params:
            self.device_params["username"] = username
        if password and "password" not in self.device_params:
            self.device_params["password"] = password
            
        self.connection = None
        self.host = self.device_params.get("host")
        self.hostname = self.device_params.get("hostname", self.host)

    def _get_valid_netmiko_params(self):
        netmiko_keys = {"device_type", "host", "ip", "username", "password", "port", "secret", "verbose"}
        
        clean_dict = {k: v for k, v in self.device_params.items() if k in netmiko_keys}
        
        clean_dict["disabled_algorithms"] = {
            "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
        }
        
        clean_dict["use_keys"] = False
        
        return clean_dict


    def __enter__(self):
        print(f">> Connecting to {self.host}...")
        clean_params = self._get_valid_netmiko_params()
        try:
            self.connection = ConnectHandler(**clean_params)
            
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            if not self.host:
                self.host = getattr(self.connection, "remote_ip", "Unknown_IP")
                
            print(f"-- Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"!! Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"<< Disconnected from {self.hostname}.\n")
        return False




    def send_cmd(self, command, **kwargs):
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        try:
            self.connection.send_config_set(
                commands, 
                cmd_verify=False, 
                config_mode_command=""
            )
            return True
        except Exception as e:
            print(f"!! ERROR: Configuration deployment fault: {e}")
            return False

    def get_config(self):
        """Retrieves the current running configuration of the EXOS switch."""
        print(f"-- Retrieving configuration from {self.hostname}...")
        return self.connection.send_command("show configuration")

    def get_vlans(self):
        """Retrieves raw VLAN information from the switch."""
        print(f"-- Retrieving VLAN configuration from {self.hostname}...")
        return self.connection.send_command("show vlan")

    def create_vlan(self, vlan_id, vlan_name):
        """Creates a VLAN and assigns a description name to it."""
        print(f"-- Creating VLAN {vlan_id} ({vlan_name}) on {self.hostname}...")
        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        output = self.connection.send_config_set(commands)
        return output

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        """Configures VLAN ports."""
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        print(f"-- Adding ports {ports_str} to {vlan_name}...")
        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        return self.connection.send_config_set([command])


    def verify_vlan_exists(self, vlan_id, vlan_name):
        """Checks the global 'show vlan' output to ensure the Name and ID match on the same line."""
        print(f"-- Checking VLAN configuration for {vlan_name} ({vlan_id})...")
        
        output = self.connection.send_command("show vlan")
        
        for line in output.splitlines():
            columns = line.strip().split()
            
            if len(columns) >= 2:
                current_name = columns[0]
                current_id = columns[1]
                
                if current_name == str(vlan_name) and current_id == str(vlan_id):
                    print(f"-- Found {vlan_name} ({vlan_id}).")
                    return True
                    
        print(f"!! NOT FOUND: {vlan_name} ({vlan_id}).")
        return False


    def save_config_primary(self):
        """Saves configuration to primary config file interactively."""
        print(f"-- Saving configuration for {self.hostname} ({self.host})...")

        output = self.connection.send_command_timing("save configuration primary")

        if "save configuration to" in output.lower() or "(y/N)" in output:
            output += self.connection.send_command_timing("y")
            
        return output


# Just an example
class CISCOManager:
    """A clean tool to handle secure CISCO switch connections."""
    def __init__(self, device_params):
        pass

