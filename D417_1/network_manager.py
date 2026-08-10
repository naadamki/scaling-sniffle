import os
from netmiko import ConnectHandler
from abc import ABC, abstractmethod

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
            print(f"       >> Connecting to {self.host}...")
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            print(f"       -- Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"       !! Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"       << Disconnected from {self.host}.")
        return False

    def send_cmd(self, command, **kwargs):
        print(f"       -- Sending command to {self.hostname}...")
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        try:
            print(f"       -- Sending commands to {self.hostname}...")
            self.connection.send_config_set(
                commands, 
                cmd_verify=False, 
                config_mode_command=""
            )
            return True
        except Exception as e:
            print(f"       !! ERROR: Configuration deployment fault: {e}")
            return False

    def get_config(self):
        print(f"       -- Getting configuration of {self.hostname}...")
        return self.connection.send_command("show configuration")

    def get_vlans(self):
        print(f"       -- Getting VLAN configuration of {self.hostname}...")
        return self.connection.send_command("show vlan")

    def create_vlan(self, vlan_id, vlan_name):

        commands = [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}"
        ]
        print(f"       -- Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")
        return self.connection.send_config_set(commands)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        if isinstance(ports, list):
            ports_str = ",".join(map(str, ports))
        else:
            ports_str = str(ports).replace(" ", "")

        tagged = "tagged" if tag else "untagged"
        command = f"configure vlan {vlan_name} add ports {ports_str} {tagged}"
        print(f"       -- Adding ports '{ports}' to VLAN '{vlan_name}' on {self.hostname}...")
        return self.connection.send_config_set([command])

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")

        print(f"       -- Verifying VLAN '{identifier}' on {self.hostname}...")
        output = self.connection.send_command(f"show vlan {identifier}")
        
        return not ("does not exist" in output.lower() or "error" in output.lower())

    def save_config_primary(self):
        output = self.connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/N)" in output:
            output += self.connection.send_command_timing("y")
        print(f"       -- Saving configuration for {self.hostname}...")    
        return output







class BaseDriver(ABC):

    @abstractmethod
    def get_config_cmd(self):
        pass

    @abstractmethod
    def get_vlans_cmd(self):
        pass

    @abstractmethod
    def get_vlan_verification_cmd(self, identifier):
        pass

    @abstractmethod
    def build_create_vlan_cmds(self, vlan_id, vlan_name):
        pass

    @abstractmethod
    def build_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        pass

    @abstractmethod
    def handle_save_config(self, connection):
        pass

    @abstractmethod
    def configure_account_password_cmd(self, account, old_pass, new_pass):
        pass


class EXOSDriver(BaseDriver):

    def get_config_cmd(self):
        return "show configuration"

    def get_vlans_cmd(self):
        return "show vlan"

    def get_vlan_verification_cmd(self, identifier):
        return f"show vlan {identifier}"

    def build_create_vlan_cmds(self, vlan_id, vlan_name):
        return [
            f"create vlan {vlan_name}",
            f"configure vlan {vlan_name} tag {vlan_id}",
        ]

    def build_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        tagged = "tagged" if tag else "untagged"
        return [f"configure vlan {vlan_name} add ports {ports_str} {tagged}"]

    def configure_account_password_cmd(self, account, old_pass, new_pass):
        # return [f'configure account {account} password "{old_pass}" {new_pass}']
        return []

    def handle_save_config(self, connection):
        output = connection.send_command_timing("save configuration primary")
        if "save configuration to" in output.lower() or "(y/n)" in output.lower():
            output += connection.send_command_timing("y")
        return output

    def run_password_rotation(self, manager_instance, account, old_pass, new_pass):
        conn = manager_instance.connection        
        print(f" -- Initiating live operational sequence for '{account}'...")
        out1 = conn.send_command("configure account admin password", cmd_verify=False, delay_factor=2)
        payload_old = f"{old_pass}\n" if old_pass else "\n"
        out2 = conn.send_command(payload_old, cmd_verify=False, delay_factor=2)
        out3 = conn.send_command(f"{new_pass}\n", cmd_verify=False, delay_factor=2)
        final_output = conn.send_command(f"{new_pass}\n", cmd_verify=False, delay_factor=2)
        return f"{out1}\n{out2}\n{out3}\n{final_output}"


# EXAMPLE
class CiscoDriver(BaseDriver):

    def get_config_cmd(self):
        return "show running-config"

    def get_vlans_cmd(self):
        return "show vlan brief"

    def get_vlan_verification_cmd(self, identifier):
        return f"show vlan id {identifier}"

    def build_create_vlan_cmds(self, vlan_id, vlan_name):
        return []

    def build_add_vlan_ports_cmds(self, vlan_name, ports_str, tag: bool):
        return []

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
            print(f"  >>  Connecting to {self.host} ({self.device_type})...")
            self.connection = ConnectHandler(**clean_params)
            if not self.hostname or self.hostname == self.host:
                self.hostname = self.connection.base_prompt.rstrip(" #> ").strip()
            print(f"  --  Connected to {self.hostname}.")
            return self
        except Exception as e:
            print(f"  !!  Connection failure to {self.host}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
            print(f"  <<  Disconnected from {self.host}.")
        return False

    def send_cmd(self, command, **kwargs):
        print(f"  --  Sending command to {self.hostname}...")
        return self.connection.send_command(command, **kwargs)

    def send_config(self, commands):
        if not commands:
            print(f"  --  No commands provided for execution on {self.hostname}.")
            return ""
        try:
            print(f"  --  Sending configuration commands to {self.hostname}...")
            output = self.connection.send_config_set(
                commands, cmd_verify=False, config_mode_command=""
            )
            return output
        except Exception as e:
            print(f"  !!  ERROR: Configuration deployment fault on {self.hostname}.")
            return f"  !!  {e}"

    def get_config(self):
        print(f"  --  Getting configuration of {self.hostname}...")
        return self.connection.send_command(self.driver.get_config_cmd())

    def get_vlans(self, structured=False):
        print(f"  --  Getting VLAN configuration of {self.hostname}...")
        cmd = self.driver.get_vlans_cmd()

        if structured:
            return self.connection.send_command(cmd, use_textfsm=True)
        return self.connection.send_command(cmd)

    def create_vlan(self, vlan_id, vlan_name):
        print(f"  --  Creating VLAN {vlan_name} ({vlan_id}) on {self.hostname}...")
        cmds = self.driver.build_create_vlan_cmds(vlan_id, vlan_name)
        return self.send_config(cmds)

    def add_vlan_ports(self, vlan_name, ports, tag=True):
        ports_str = (
            ",".join(map(str, ports))
            if isinstance(ports, list)
            else str(ports).replace(" ", "")
        )
        print(
            f"  --  Adding ports '{ports_str}' to VLAN '{vlan_name}' on {self.hostname}..."
        )
        cmds = self.driver.build_add_vlan_ports_cmds(vlan_name, ports_str, tag)
        return self.send_config(cmds)

    def verify_vlan_exists(self, vlan_id=None, vlan_name=None) -> bool:
        identifier = str(vlan_id) if vlan_id is not None else vlan_name
        if not identifier:
            raise ValueError("Must provide either vlan_id or vlan_name to verify.")
        print(f"  --  Verifying VLAN '{identifier}' on {self.hostname}...")
        output = self.connection.send_command(
            self.driver.get_vlan_verification_cmd(identifier)
            )
        return not ("does not exist" in output.lower() or "error" in output.lower())

    # def configure_account_password(self, account, old_pass, new_pass):
    #     print(f"  --  Changing {account} password on {self.hostname}...")
    #     cmds = self.driver.configure_account_password_cmd(
    #         account, old_pass, new_pass
    #     )
    #     return self.send_config(cmds)

    # def configure_account_password(self, account, old_pass, new_pass):
    #     print(f"  --  Changing {account} password on {self.hostname}...")
    #     cmds = self.driver.configure_account_password_cmd(account, old_pass, new_pass)
        
    #     output = self.send_config(cmds)
        
    #     error_keywords = ["error", "invalid", "denied", "incorrect", "syntax", "fail"]
        
    #     if any(keyword in output.lower() for keyword in error_keywords):
    #         print(f"  !!  VALIDATION CRITICAL FAILURE on {self.hostname}!")
    #         print(f"  !!  [Raw Output Log From Device]:\n  !!  {output}")
            
    #         raise RuntimeError(f"  !!  Switch rejected password configuration command due to a syntax/auth error.")
            
    #     print(f"  --  Validation check passed. Password command applied successfully.")
    #     return True

    def configure_account_password(self, account, old_pass, new_pass):
        print(f"  --  Changing {account} password on {self.hostname}...")
        
        if self.device_type == "extreme_exos":
            output = self.driver.run_password_rotation(self, account, old_pass, new_pass)
        else:
            cmds = self.driver.configure_account_password_cmd(account, old_pass, new_pass)
            output = self.send_config(cmds)
            
        error_keywords = ["error", "invalid", "denied", "incorrect", "fail", "mismatch"]
        if any(keyword in output.lower() for keyword in error_keywords):
            print(f"  !!  VALIDATION CRITICAL FAILURE on {self.hostname}!")
            print(f"  !!  [Raw Output Log From Device]:\n{output}")
            raise RuntimeError("Switch rejected password change conversation due to authentication or formatting errors.")
            
        print(f"  --  Validation check passed. Password applied successfully.")
        return True



    def save_config_primary(self):
        print(f"  --  Saving configuration for {self.hostname}...")
        return self.driver.handle_save_config(self.connection)




