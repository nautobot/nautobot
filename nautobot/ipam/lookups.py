import netaddr
from django.db import NotSupportedError
from django.db import connection as _connection
from django.db.models import Lookup, lookups


def _mysql_varbin_to_broadcast():
    return "HEX(broadcast)"


def _mysql_varbin_to_hex(lhs):
    return f"HEX({lhs})"


def _mysql_varbin_to_network():
    return "HEX(network)"


def _postgresql_varbin_to_broadcast(length):
    return f"right(broadcast::text, -1)::varbit::bit({length})"


def _postgresql_varbin_to_integer(lhs, length):
    return f"right({lhs}::text, -1)::varbit::bit({length})"


def _postgresql_varbin_to_network(lhs, length):
    # convert to bitstring, 0 out everything larger than prefix_length
    return f"lpad(right({lhs}::text, -1)::varbit::text, prefix_length, '0')::bit({length})"


def py_to_hex(ip, length):
    return str(hex(int(ip)))[2:].zfill(int(length / 4))


def get_ip_info(field_name, ip_str):
    """Function to set all details about an IP, that may be needed."""
    ip_details = IPDetails()
    ip = netaddr.IPNetwork(ip_str)
    if field_name == "network":
        ip_details.addr = ip.network
    elif field_name == "host":
        ip_details.addr = ip.ip
    ip_details.ip = ip
    ip_details.prefix = ip.prefixlen
    ip_details.length = ip_details.to_len[ip.version]

    if _connection.vendor == "mysql":
        ip_details.rhs = py_to_hex(ip.ip, ip_details.length)
        ip_details.net_addr = f"'{py_to_hex(ip.network, ip_details.length)}'"
        ip_details.bcast_addr = f"'{py_to_hex(ip[-1], ip_details.length)}'"
        ip_details.q_net = _mysql_varbin_to_network()
        ip_details.q_bcast = _mysql_varbin_to_broadcast()
        ip_details.q_ip = _mysql_varbin_to_hex(field_name)

    elif _connection.vendor == "postgresql":
        ip_details.rhs = bin(int(ip_details.addr))[2:].zfill(ip_details.length)
        ip_details.addr_str = f"B'{bin(int(ip_details.addr))[2:].zfill(ip_details.length)}'"
        ip_details.net_addr = f"B'{bin(int(ip.network))[2:].zfill(ip_details.length)}'"
        ip_details.bcast_addr = f"B'{bin(int(ip[-1]))[2:].zfill(ip_details.length)}'"
        ip_details.q_net = _postgresql_varbin_to_network(field_name, ip_details.length)
        ip_details.q_bcast = _postgresql_varbin_to_broadcast(ip_details.length)
        ip_details.q_ip = _postgresql_varbin_to_integer(field_name, ip_details.length)

    return ip_details


class IPDetails:
    """Class for setting up all details about an IP they may be needed"""

    net = None
    addr = None
    ip = None
    prefix = None
    length = None
    addr_str = None
    rhs = None
    net_addr = None
    bcast_addr = None
    q_net = None
    q_bcast = None
    q_ip = None
    to_len = {4: 32, 6: 128}


class StringMatchMixin:
    def process_lhs(self, qn, connection, lhs=None):
        lhs = lhs or self.lhs
        lhs_string, lhs_params = qn.compile(lhs)
        if connection.vendor == "postgresql":
            raise NotSupportedError("Lookup not supported on postgresql.")
        return f"INET6_NTOA({lhs_string})", lhs_params


class Exact(StringMatchMixin, lookups.Exact):
    pass


class IExact(StringMatchMixin, lookups.IExact):
    pass


class EndsWith(StringMatchMixin, lookups.EndsWith):
    pass


class IEndsWith(StringMatchMixin, lookups.IEndsWith):
    pass


class StartsWith(StringMatchMixin, lookups.StartsWith):
    pass


class IStartsWith(StringMatchMixin, lookups.IStartsWith):
    pass


class Regex(StringMatchMixin, lookups.Regex):
    pass


class IRegex(StringMatchMixin, lookups.IRegex):
    pass


class NetworkFieldMixin:
    def get_prep_lookup(self):
        field_name = self.lhs.field.name
        if field_name not in ["host", "network"]:
            raise NotSupportedError(f"Lookup only provided on the host and network fields, not {field_name}.")
        if field_name == "network" and self.lookup_name in ["net_host", "net_host_contained", "net_in"]:
            raise NotSupportedError(f"Lookup for network field does not include the {self.lookup_name} lookup.")
        if field_name == "host" and self.lookup_name not in ["net_host", "net_host_contained", "net_in"]:
            raise NotSupportedError(f"Lookup for host field does not include the {self.lookup_name} lookup.")
        self.ip = get_ip_info(field_name, self.rhs)
        return str(self.ip.ip)

    def process_rhs(self, qn, connection):
        sql, params = super().process_rhs(qn, connection)
        params[0] = self.ip.rhs
        return sql, params


class NetEquals(NetworkFieldMixin, Lookup):
    lookup_name = "net_equals"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"prefix_length = {self.ip.prefix} AND {rhs} = {self.ip.q_ip}"
        return query, lhs_params + rhs_params


class NetContainsOrEquals(NetworkFieldMixin, Lookup):
    lookup_name = "net_contains_or_equals"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"prefix_length <= {self.ip.prefix} AND {rhs} BETWEEN {self.ip.q_net} AND {self.ip.q_bcast}"
        return query, lhs_params + rhs_params


class NetContains(NetworkFieldMixin, Lookup):
    lookup_name = "net_contains"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"prefix_length < {self.ip.prefix} AND {rhs} BETWEEN {self.ip.q_net} AND {self.ip.q_bcast}"
        return query, lhs_params + rhs_params


class NetContainedOrEqual(NetworkFieldMixin, Lookup):
    lookup_name = "net_contained_or_equal"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"prefix_length >= {self.ip.prefix} AND {self.ip.q_net} BETWEEN {rhs} AND {self.ip.bcast_addr}"
        return query, lhs_params + rhs_params


class NetContained(NetworkFieldMixin, Lookup):
    lookup_name = "net_contained"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"prefix_length > {self.ip.prefix} AND {self.ip.q_net} BETWEEN {rhs} AND {self.ip.bcast_addr}"
        return query, lhs_params + rhs_params


class NetHost(Lookup):
    lookup_name = "net_host"

    def get_prep_lookup(self):
        field_name = self.lhs.field.name
        if field_name != "host":
            raise NotSupportedError(f"Lookup only provided on the host fields, not {field_name}.")
        self.ip = get_ip_info(field_name, self.rhs)
        return str(self.ip.ip)

    def process_rhs(self, qn, connection):
        sql, params = super().process_rhs(qn, connection)
        params[0] = self.ip.rhs
        return sql, params

    def process_lhs(self, qn, connection, lhs=None):
        lhs = lhs or self.lhs
        _, lhs_params = qn.compile(lhs)
        return self.ip.q_ip, lhs_params

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        return f"{lhs} = {rhs}", lhs_params + rhs_params


class NetIn(Lookup):
    lookup_name = "net_in"

    def get_prep_lookup(self):
        field_name = self.lhs.field.name
        if field_name != "host":
            raise NotSupportedError(f"Lookup only provided on the host field, not {field_name}.")
        self.ips = []
        for _ip in self.rhs:
            ip = get_ip_info(field_name, _ip)
            self.ips.append(ip)
        # This is to satisfy an issue with django cacheops, specifically this line:
        # https://github.com/Suor/django-cacheops/blob/a5ed1ac28c7259f5ad005e596cc045d1d61e2c51/cacheops/query.py#L175
        # Without 1, and one 1 value as %s, will result in stacktrace. A non-impacting condition is added to the query
        if _connection.vendor == "mysql":
            self.query_starter = "'1' NOT IN %s AND "
        elif _connection.vendor == "postgresql":
            self.query_starter = "'1' != ANY(%s) AND "
        return self.rhs

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        _, rhs_params = self.process_rhs(qn, connection)
        query = self.query_starter
        query += "OR ".join(f"{ip.q_ip} BETWEEN {ip.net_addr} AND {ip.bcast_addr} " for ip in self.ips)
        return query, lhs_params + rhs_params


class NetHostContained(NetworkFieldMixin, Lookup):
    lookup_name = "net_host_contained"

    def as_sql(self, qn, connection):
        _, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        query = f"{self.ip.q_ip} BETWEEN {rhs} AND {self.ip.bcast_addr}"
        return query, lhs_params + rhs_params


class NetFamily(Lookup):
    lookup_name = "family"

    def get_prep_lookup(self):
        if self.rhs not in [4, 6]:
            raise NotSupportedError("Family must be either integer of value 4 or 6")
        if self.rhs == 6:
            self.rhs = 16
        return self.rhs

    def process_lhs(self, qn, connection, lhs=None):
        lhs = lhs or self.lhs
        lhs_string, lhs_params = qn.compile(lhs)
        return f"LENGTH({lhs_string})", lhs_params

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        return f"{lhs} = {rhs}", lhs_params + rhs_params
