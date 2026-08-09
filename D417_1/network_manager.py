import os
import json
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from netmiko import ConnectHandler

# Suppress warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EXOSHTTPSManager:
    """Handles EXOS management over HTTPS REST API (EXREST)."""

    def __init__(self, device_params, username=None, password=None, use_ssl=True, timeout=15):
        # Normalize input whether passed as a dictionary from YAML or a plain string IP
        if isinstance(device_params, dict):
            self.device_params = device_params.copy()
            self.host = self.device_params.get("host")
            self.hostname = self.device_params.get("hostname", self.host)
            # Use explicit args if provided, otherwise fall back to dictionary values or defaults
            self.username = username or self.device_params.get("username", "admin")
            self.password = password if password is not None else self.device_params.get("password", "")
        else:
            self.host = str(device_params)
            self.hostname = self.host
            self.username = username or "admin"
            self.password = password if password is not None else ""
            self.device_params = {"host": self.host}

        self.protocol = "https" if use_ssl else "http"
        self.base_url = f"{self.protocol}://{self.host}/rest/v1/exos"
        self.timeout = timeout
        self.session = None

    def __enter__(self):
        print(f"    >> Beginning HTTPS session with {self.hostname} ({self.host})...")
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.verify = False  # Bypasses self-signed SSL cert checks
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
            print(f"    << Disconnected HTTPS session with {self.hostname}.\n")
        return False

    def run_cli(self, command) -> dict:
        url = f"{self.base_url}/cli"
        if isinstance(command, list):
            results = []
            for cmd in command:
                payload = {"cli": cmd}
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                results.append(resp.json())
                print(f"    -- Running {command} on {self.hostname}")
            return {"results": results}
        else:
            payload = {"cli": command}
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            print(f"    -- Running {command} on {self.hostname}")
            return resp.json()

    def get_config(self) -> str:
        result = self.run_cli("show configuration")
        print(f"    -- Getting current configuration from {self.hostname}...")
        return json.dumps(result, indent=2)

    def get_vlans(self) -> str:
        result = self.run_cli("show vlan")
        print(f"    -- Getting VLAN configuration from {self.hostname}...")        
        return json.dumps(result, indent=2)

    def create_vlan(self, vlan_id, vlan_name):
        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        result = self.run_cli(commands)
        print(f"    -- Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")        
        return json.dumps(result, indent=2)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        result = self.run_cli(command)
        return json.dumps(result, indent=2)

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        # Use vlan_id if provided; otherwise fallback to vlan_name
        identifier = vlan_id if vlan_id is not None else vlan_name
        
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")

        print(f"    -- Verifying VLAN '{identifier}' is on {self.hostname}...")
        result = self.run_cli(f"show vlan {identifier}")
        result_str = json.dumps(result).lower()
        return not ("does not exist" in result_str or "error" in result_str)

    def save_config_primary(self):
        result = self.run_cli("save configuration primary")
        print(f"    -- Saving current configuration of {self.hostname}...")        
        return json.dumps(result, indent=2)




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
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            return self
        except Exception as e:
            print(f"    !! Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
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
            print(f"    !! ERROR: Configuration deployment fault: {e}")
            return False

    def get_config(self):
        return self.connection.send_command("show configuration")

    def get_vlans(self):
        return self.connection.send_command("show vlan")

    def create_vlan(self, vlan_id, vlan_name):
        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        return self.connection.send_config_set(commands)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        return self.connection.send_config_set([command])

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")

        print(f"    -- Verifying VLAN '{identifier}' is on {self.hostname}...")
        
        output = self.connection.send_command(f"show vlan {identifier}")
        
        return not ("does not exist" in output.lower() or "error" in output.lower())

    def save_config_primary(self):
        output = self.connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/N)" in output:
            output += self.connection.send_command_timing("y")
        return output