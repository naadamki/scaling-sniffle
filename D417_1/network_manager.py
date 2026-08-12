from netmiko import ConnectHandler
from abc import ABC, abstractmethod
import yaml
import re



import re

def parse_exos_show_vlan(raw_cli_output):
    vlan_list = []

    pattern = re.compile(
        r"^(?P<name>\S+)\s+"
        r"(?P<vid>\d+)\s+"
        r"(?P<protocol>\S+)\s+"
        r"(?P<addr>\S+)\s+"          
        r"(?P<flags>[\s\w!*gtbpmeuLGHU-]+?)\s+" 
        r"(?P<active_ports>\d+)\s*/\s*(?P<total_ports>\d+)\s+"
        r"(?P<vr>\S+)",
        re.MULTILINE,
    )
    
    for match in pattern.finditer(raw_cli_output):
        data = match.groupdict()
        ip_addr = data["addr"]
        if "-" in ip_addr:
            ip_addr = None
            
        vlan_list.append({
            "name": data["name"],
            "vid": data["vid"],
            "ip_address": ip_addr,
            "active_ports": data["active_ports"],
            "total_ports": data["total_ports"],
            "vr": data["vr"]
        })
        
    return vlan_list
    # [
    #     {
    #         'name': 'Default', 
    #         'vid': '1', 
    #         'flags': '------------T--------------', 
    #         'protocol': 'ANY', 
    #         'active_ports': '2', 
    #         'total_ports': '12', 
    #         'vr': 'VR-Default', 
    #         'ip_address': '10.10.1.22/24'
    #     },
    # ]




class InventoryManager:

    def __init__(self, inventory_file, closet_name=None):
        self.inventory_file = inventory_file
        self.closet_name = closet_name
        self.raw_data = self._load_yaml()

    def _load_yaml(self):
        with open(self.inventory_file, 'r') as f:
            return yaml.safe_load(f)

    @property
    def building_name(self):
        return self.raw_data.get('building_name', 'Unknown')

    @property
    def available_closets(self):
        return list(self.raw_data.get('inventory', {}).keys())

    @property
    def devices(self):
        if not self.closet_name:
            raise ValueError("Closet name must be set before accessing devices.")

        all_closets = self.raw_data.get('inventory', {})
        if self.closet_name not in all_closets:
            raise KeyError(
                f"!!  Closet '{self.closet_name}' not found in {self.inventory_file}. Available: {self.available_closets}"
            )

        return all_closets[self.closet_name]

    @property
    def aggregate_switches(self):
        return [dev for dev in self.devices if dev.get('role') == 'aggregate']

    @property
    def access_switches(self):
        return [dev for dev in self.devices if dev.get('role') == 'access']

    def get_vlan_definitions(self):
        vlan_configs = []
        for dev in self.devices:
            vlan_id = dev.get('vlan_id', 0)
            if vlan_id > 0:
                vlan_configs.append({
                    'hostname': dev.get('hostname'),
                    'vlan_name': dev.get('vlan_name'),
                    'vlan_id': vlan_id,
                    'access_ports': dev.get('access_ports', 'None'),
                    'uplink_port': dev.get('uplink_port', 'None'),
                    'core_trunk_port': dev.get('core_trunk_port', 'None'),
                })
        return vlan_configs

    def build_required_vlan_map(self):
        required_vlans= {device['hostname']: [] for device in self.devices}

        for switch in self.access_switches:
            id = switch.get("vlan_id")
            name = switch.get("vlan_name")
            up_port = switch.get("uplink_port")
            acc_ports = switch.get("access_ports")
            trunk_port = switch.get("core_trunk_port")

            acc_tuple = (id, name, up_port, acc_ports)
            required_vlans[switch['hostname']].append(acc_tuple)

            agg_tuple = (id, name, trunk_port, "None")
            for agg in self.aggregate_switches:
                required_vlans[agg['hostname']].append(agg_tuple)
        return required_vlans




    def __iter__(self):
        return iter(self.devices)

    def __len__(self):
        return len(self.devices)



class BaseDriver(ABC):

    @abstractmethod
    def get_config_cmd(self):
        pass

    @abstractmethod
    def get_vlans_cmd(self):
        pass

    @abstractmethod
    def get_parse_vlans_cmd(self, raw_cli_output):
        pass

    @abstractmethod
    def get_vlan_verification_cmd(self, identifier):
        pass

    @abstractmethod
    def get_create_vlan_cmds(self, vlan_id, vlan_name):
        pass

    @abstractmethod
    def get_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        pass

    @abstractmethod
    def get_create_service_account_cmds(self, username, password, access_level="admin"):
        pass

    @abstractmethod
    def handle_save_config(self, connection):
        pass



class EXOSDriver(BaseDriver):

    def get_config_cmd(self):
        return "show configuration"

    def get_vlans_cmd(self):
        return "show vlan"

    def get_parse_vlans_cmd(self, raw_cli_output):
        return parse_exos_show_vlan(raw_cli_output)

    def get_vlan_verification_cmd(self, identifier):
        return f"show vlan {identifier}"

    def get_create_vlan_cmds(self, vlan_id, vlan_name):
        return [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}",
        ]

    def get_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        tagged = "tagged" if tag else "untagged"
        return [f"configure vlan {vlan_name} add ports {ports_str} {tagged}"]

    def get_create_service_account_cmds(self, username, password, access_level="admin"):
        return [
            f"create account {access_level} {username} {password}"
        ]

    def handle_save_config(self, connection):
        output = connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/n)" in output.lower():
            output += connection.send_command_timing("y")
        return output



# EXAMPLE
class CiscoDriver(BaseDriver):

    def get_config_cmd(self):
        return "show running-config"

    def get_parse_vlans_cmd(raw_cli_output):
        return []

    def get_vlans_cmd(self):
        return "show vlan brief"

    def get_vlan_verification_cmd(self, identifier):
        return f"show vlan id {identifier}"

    def get_create_vlan_cmds(self, vlan_id, vlan_name):
        return []

    def get_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        return []
    
    def get_create_service_account_cmds(
        self, username, password, access_level="admin"
    ):
        return [f"username {username} privilege 15 password {password}"]

    def handle_save_config(self, connection):
        return connection.send_command("write memory")


class DeviceManager:
    _DRIVERS = {"extreme_exos": EXOSDriver, "cisco_ios": CiscoDriver}

    def __init__(
        self, device_params, device_type=None, username=None, password=None
    ):
        if isinstance(device_params, dict):
            self.device_params = device_params.copy()
        else:
            self.device_params = {"host": str(device_params)}

        extracted_type = (
            self.device_params.get("device_type") or device_type or "extreme_exos"
        )
        self.device_type = extracted_type.lower()

        if self.device_type not in self._DRIVERS:
            raise ValueError(f"Unsupported device type: {self.device_type}")

        self.driver = self._DRIVERS[self.device_type]()

        if username and "username" not in self.device_params:
            self.device_params["username"] = username
        if password is not None and "password" not in self.device_params:
            self.device_params["password"] = password

        self.host = self.device_params.get("host")
        self.hostname = self.device_params.get("hostname", self.host)
        self.connection = None

    def _get_valid_netmiko_params(self):
        netmiko_keys = {
            "host",
            "ip",
            "username",
            "password",
            "port",
            "secret",
            "verbose",
        }
        clean_dict = {
            k: v for k, v in self.device_params.items() if k in netmiko_keys
        }
        clean_dict["device_type"] = self.device_type

        if not clean_dict.get("password"):
            clean_dict["device_type"] = f"{self.device_type}_telnet"
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
            print(f">>  Connecting to {self.host} ({self.device_type})...")
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            self.connection.send_command("disable clipaging")
            print(f"--  Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"!!  Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"<<  Disconnected from {self.host}.")
        return False

    def send_cmd(self, command, **kwargs):
        print(f"--  Sending command to {self.hostname}...")
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        if not commands:
            print(f"--  No commands provided for execution on {self.hostname}.")
            return ""
        try:
            print(f"--  Sending configuration commands to {self.hostname}...")
            output = self.connection.send_config_set(
                commands, cmd_verify=False, config_mode_command=""
            )
            return output
        except Exception as e:
            print(f"!!  ERROR: Configuration deployment fault on {self.hostname}.")
            return f"!!  {e}"

    def get_config(self):
        print(f"--  Getting configuration of {self.hostname}...")
        return self.connection.send_command(self.driver.get_config_cmd())

    def get_vlans(self, parse=True):
        print(f"--  Getting VLAN configuration of {self.hostname}...")
        cmd = self.driver.get_vlans_cmd()
        raw_output = self.connection.send_command(cmd)

        if parse:
            return self.driver.get_parse_vlans_cmd(raw_output)
        return raw_output

    def create_vlan(self, vlan_id, vlan_name):
        print(f"--  Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")
        cmds = self.driver.get_create_vlan_cmds(vlan_id, vlan_name)
        return self.send_config(cmds)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        ports_str = (
            ",".join(map(str, ports))
            if isinstance(ports, list)
            else str(ports).replace(" ", "")
        )
        print(
            f"--  Adding ports '{ports_str}' to VLAN '{vlan_name}' on {self.hostname}..."
        )
        cmds = self.driver.get_add_vlan_ports_cmds(vlan_name, ports_str, tag)
        return self.send_config(cmds)

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")
        print(f"--  Verifying VLAN '{identifier}' on {self.hostname}...")
        output = self.connection.send_command(
            self.driver.get_vlan_verification_cmd(identifier)
            )
        return not ("does not exist" in output.lower() or "error" in output.lower())

    def create_service_account(self, username, password, access_level="admin"):
        print(f"--  Provisioning automation service account '{username}' on {self.hostname}...")
        cmds = self.driver.get_create_service_account_cmds(username, password, access_level)
        return self.send_config(cmds)

    def save_config_primary(self):
        print(f"--  Saving configuration for {self.hostname}...")
        return self.driver.handle_save_config(self.connection)




# First implementation...then evolved into a more abstract and DRY form
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
            print(f"     >> Connecting to {self.host}...")
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            print(f"     -- Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"     !! Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"     << Disconnected from {self.host}.")
        return False

    def send_cmd(self, command, **kwargs):
        print(f"     -- Sending command to {self.hostname}...")
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        try:
            print(f"     -- Sending commands to {self.hostname}...")
            self.connection.send_config_set(
                commands, 
                cmd_verify=False, 
                config_mode_command=""
            )
            return True
        except Exception as e:
            print(f"     !! ERROR: Configuration deployment fault: {e}")
            return False

    def get_config(self):
        print(f"     -- Getting configuration of {self.hostname}...")
        return self.connection.send_command("show configuration")

    def get_vlans(self):
        print(f"     -- Getting VLAN configuration of {self.hostname}...")
        return self.connection.send_command("show vlan")

    def create_vlan(self, vlan_id, vlan_name):

        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        print(f"     -- Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")
        return self.connection.send_config_set(commands)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        print(f"     -- Adding ports '{ports}' to VLAN '{vlan_name}' on {self.hostname}...")
        return self.connection.send_config_set([command])

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")

        print(f"     -- Verifying VLAN '{identifier}' on {self.hostname}...")
        output = self.connection.send_command(f"show vlan {identifier}")
        
        return not ("does not exist" in output.lower() or "error" in output.lower())

    def save_config_primary(self):
        output = self.connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/N)" in output:
            output += self.connection.send_command_timing("y")
        print(f"     -- Saving configuration for {self.hostname}...")    
        return output
