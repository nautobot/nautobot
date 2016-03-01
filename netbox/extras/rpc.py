from Exscript import Account
from Exscript.protocols import SSH2
from ncclient import manager
import paramiko
import re
import xmltodict


CONNECT_TIMEOUT = 5  # seconds


class RPCClient(object):

    def __init__(self, device, username='', password=''):
        self.username = username
        self.password = password
        try:
            self.host = str(device.primary_ip.address.ip)
        except AttributeError:
            raise Exception("Specified device ({}) does not have a primary IP defined.".format(device))

    def get_lldp_neighbors(self):
        """
        Returns a list of dictionaries, each representing an LLDP neighbor adjacency.

        {
            'local-interface': <str>,
            'name': <str>,
            'remote-interface': <str>,
            'chassis-id': <str>,
        }
        """
        raise NotImplementedError("Feature not implemented for this platform.")

    def get_inventory(self):
        """
        Returns a dictionary representing the device chassis and installed modules.

        {
            'chassis': {
                'serial': <str>,
                'description': <str>,
            }
            'modules': [
                {
                    'name': <str>,
                    'part_id': <str>,
                    'serial': <str>,
                },
                ...
            ]
        }
        """
        raise NotImplementedError("Feature not implemented for this platform.")


class JunosNC(RPCClient):
    """
    NETCONF client for Juniper Junos devices
    """

    def __enter__(self):

        # Initiate a connection to the device
        self.manager = manager.connect(host=self.host, username=self.username, password=self.password,
                                       hostkey_verify=False, timeout=CONNECT_TIMEOUT)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        # Close the connection to the device
        self.manager.close_session()

    def get_lldp_neighbors(self):

        rpc_reply = self.manager.dispatch('get-lldp-neighbors-information')
        lldp_neighbors_raw = xmltodict.parse(rpc_reply.xml)['rpc-reply']['lldp-neighbors-information']['lldp-neighbor-information']

        result = []
        for neighbor_raw in lldp_neighbors_raw:
            neighbor = dict()
            neighbor['local-interface'] = neighbor_raw.get('lldp-local-port-id')
            neighbor['name'] = neighbor_raw.get('lldp-remote-system-name')
            neighbor['name'] = neighbor['name'].split('.')[0]  # Split hostname from domain if one is present
            try:
                neighbor['remote-interface'] = neighbor_raw['lldp-remote-port-description']
            except KeyError:
                # Older versions of Junos report on interface ID instead of description
                neighbor['remote-interface'] = neighbor_raw.get('lldp-remote-port-id')
            neighbor['chassis-id'] = neighbor_raw.get('lldp-remote-chassis-id')
            result.append(neighbor)

        return result

    def get_inventory(self):

        rpc_reply = self.manager.dispatch('get-chassis-inventory')
        inventory_raw = xmltodict.parse(rpc_reply.xml)['rpc-reply']['chassis-inventory']['chassis']

        result = dict()

        # Gather chassis data
        result['chassis'] = {
            'serial': inventory_raw['serial-number'],
            'description': inventory_raw['description'],
        }

        # Gather modules
        result['modules'] = []
        for module in inventory_raw['chassis-module']:
            try:
                # Skip built-in modules
                if module['name'] and module['serial-number'] != inventory_raw['serial-number']:
                    result['modules'].append({
                        'name': module['name'],
                        'part_id': module['model-number'] or '',
                        'serial': module['serial-number'] or '',
                    })
            except KeyError:
                pass

        return result


class IOSSSH(RPCClient):
    """
    SSH client for Cisco IOS devices
    """

    def __enter__(self):

        # Initiate a connection to the device
        self.ssh = SSH2(connect_timeout=CONNECT_TIMEOUT)
        self.ssh.connect(self.host)
        self.ssh.login(Account(self.username, self.password))

        # Disable terminal paging
        self.ssh.execute("terminal length 0")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        # Close the connection to the device
        self.ssh.send("exit\r")
        self.ssh.close()

    def get_inventory(self):

        result = dict()

        # Gather chassis data
        try:
            self.ssh.execute("show version")
            show_version = self.ssh.response
            serial = re.search("Processor board ID ([^\s]+)", show_version).groups()[0]
            description = re.search("\r\n\r\ncisco ([^\s]+)", show_version).groups()[0]
        except:
            raise RuntimeError("Failed to glean chassis info from device.")
        result['chassis'] = {
            'serial': serial,
            'description': description,
        }

        # Gather modules
        result['modules'] = []
        try:
            self.ssh.execute("show inventory")
            show_inventory = self.ssh.response
            # Split modules on double line
            modules_raw = show_inventory.strip().split('\r\n\r\n')
            for module_raw in modules_raw:
                try:
                    m_name = re.search('NAME: "([^"]+)"', module_raw).group(1)
                    m_pid = re.search('PID: ([^\s]+)', module_raw).group(1)
                    m_serial = re.search('SN: ([^\s]+)', module_raw).group(1)
                    # Omit built-in modules and those with no PID
                    if m_serial != result['chassis']['serial'] and m_pid.lower() != 'unspecified':
                        result['modules'].append({
                            'name': m_name,
                            'part_id': m_pid,
                            'serial': m_serial,
                        })
                except AttributeError:
                    continue
        except:
            raise RuntimeError("Failed to glean module info from device.")

        return result


class OpengearSSH(RPCClient):
    """
    SSH client for Opengear devices
    """

    def __enter__(self):

        # Initiate a connection to the device
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.host, username=self.username, password=self.password, timeout=CONNECT_TIMEOUT)
        except paramiko.AuthenticationException:
            # Try default Opengear credentials if the configured creds don't work
            self.ssh.connect(self.host, username='root', password='default')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        # Close the connection to the device
        self.ssh.close()

    def get_inventory(self):

        try:
            stdin, stdout, stderr = self.ssh.exec_command("showserial")
            serial = stdout.readlines()[0].strip()
        except:
            raise RuntimeError("Failed to glean chassis serial from device.")
        # Older models don't provide serial info
        if serial == "No serial number information available":
            serial = ''

        try:
            stdin, stdout, stderr = self.ssh.exec_command("config -g config.system.model")
            description = stdout.readlines()[0].split(' ', 1)[1].strip()
        except:
            raise RuntimeError("Failed to glean chassis description from device.")

        return {
            'chassis': {
                'serial': serial,
                'description': description,
            },
            'modules': [],
        }


# For mapping platform -> NC client
RPC_CLIENTS = {
    'juniper-junos': JunosNC,
    'cisco-ios': IOSSSH,
    'opengear': OpengearSSH,
}
