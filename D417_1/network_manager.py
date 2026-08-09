import os
from netmiko import ConnectHandler

class EXOSManager:
    """Handles EXOS management over SSH/Telnet using Netmiko."""

    def __init__(self, device_params, username=None, password=None):
        if isinstance(device_params, dict):
            self.device_params = device_params.copy()
        else:
            self.device_params = {"host": str(device_params)}

        if username and "username" not in self.device_params:
            self.device_params["username"] = username
        if password is not None and "password" not in self.device_params:
            self.device_params["password"] = password

        self.host = self.device_params.get("host")
        self.hostname = self.device_params.get("hostname", self.host)
        self.connection = None

    def _get_valid_netmiko_params(self):
        netmiko_keys = {
            "device_type", "host", "ip", "username", "password",
            "port", "secret", "verbose", "use_keys"
        }
        clean_dict = {k: v for k, v in self.device_params.items() if k in netmiko_keys}

        if not clean_dict.get("password"):
            clean_dict["device_type"] = "extreme_exos_telnet"
            clean_dict["use_keys"] = False
        else:
            clean_dict["use_keys"] = False
            clean_dict["disabled_algorithms"] = {
                "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
            }
        return clean_dict

    def __enter__(self):
        clean_params = self._get_valid_netmiko_params()
        try:
            print(f"    >> Connecting to {self.host}...")
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            print(f"    -- Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"    !! Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"    << Disconnected from {self.host}.")
        return False

    def send_cmd(self, command, **kwargs):
        print(f"    -- Sending command to {self.hostname}...")
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        try:
            print(f"    -- Sending commands to {self.hostname}...")
            self.connection.send_config_set(
                commands, 
                cmd_verify=False, 
                config_mode_command=""
            )
            return True
        except Exception as e:
            print(f"    !! ERROR: Configuration deployment fault: {e}")
            return False

    def get_config(self):
        print(f"    -- Getting configuration of {self.hostname}...")
        return self.connection.send_command("show configuration")

    def get_vlans(self):
        print(f"    -- Getting VLAN configuration of {self.hostname}...")
        return self.connection.send_command("show vlan")

    def create_vlan(self, vlan_id, vlan_name):

        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        print(f"    -- Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")
        return self.connection.send_config_set(commands)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        print(f"    -- Adding ports '{ports}' to VLAN '{vlan_name}' on {self.hostname}...")
        return self.connection.send_config_set([command])

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")

        print(f"    -- Verifying VLAN '{identifier}' on {self.hostname}...")
        output = self.connection.send_command(f"show vlan {identifier}")
        
        return not ("does not exist" in output.lower() or "error" in output.lower())

    def save_config_primary(self):
        output = self.connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/N)" in output:
            output += self.connection.send_command_timing("y")
        print(f"    -- Saving configuration for {self.hostname}...")    
        return output



    