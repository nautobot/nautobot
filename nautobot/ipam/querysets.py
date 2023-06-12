import re

import netaddr
from django.core.exceptions import ValidationError
from django.db.models import F, ProtectedError, Q
from django.db.models.functions import Length

from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.ipam.constants import IPV4_BYTE_LENGTH, IPV6_BYTE_LENGTH


class RIRQuerySet(RestrictedQuerySet):
    """QuerySet for RIR objects."""

    def get_by_natural_key(self, name):
        return self.get(name=name)


class BaseNetworkQuerySet(RestrictedQuerySet):
    """Base class for network-related querysets."""

    ip_family_map = {
        4: IPV4_BYTE_LENGTH,
        6: IPV6_BYTE_LENGTH,
    }

    # Match string with ending in "::"
    RE_COLON = re.compile(".*::$")

    # Match string from "0" to "ffff" with no trailing ":"
    # Allows for abbreviated and non-abbreviated hextet forms
    RE_HEXTET = re.compile("^[a-f0-9]{4}$|^0{0,1}[a-f0-9]{3}$|^0{0,2}[a-f0-9]{2}$|^0{0,3}[a-f0-9]{1}$")

    @staticmethod
    def _get_last_ip(network):
        """
        Get the last IP address in the given network.

        This is distinct from network.broadcast in the case of point-to-point or host networks
        (neither of which technically have a "broadcast" address).
        """
        return network.broadcast if network.broadcast else network[-1]

    @staticmethod
    def _is_ambiguous_network_string(search):
        """
        Determines if an inputted search could be both a valid IPv4 or IPv6 beginning octet or hextet respectively.
        """
        return search.isdigit() and int(search) < 256

    def _safe_parse_network_string(self, search, version):
        """
        Parses a input string into an IPNetwork object of input version.
        Handles AddrFormatError exception and returns an empty address.
        """
        try:
            call_map = {
                4: self.parse_ipv4,
                6: self.parse_ipv6,
            }
            return call_map[version](search)

        except netaddr.core.AddrFormatError:
            ver_map = {4: "0/32", 6: "::/128"}
            return netaddr.IPNetwork(ver_map[version])

    def _check_and_prep_ipv6(self, search):
        """
        Checks to see if input search could be a valid IPv6 address and prepares it for parsing
        """
        # (IPv6) If the value ends with ":" but it's not "::", make it so.
        if search.endswith(":") and not self.RE_COLON.match(search):
            search += ":"
        # (IPv6) If the value has a colon in it, but doesn't end with one or
        # contain "::"
        elif all(
            [
                not search.endswith(":"),
                ":" in search,
                "::" not in search,
            ]
        ):
            search += ":"
        # (IPv6) If the value is numeric and > 255, append "::"
        # (IPv6) If the value is a hextet (e.g. "fe80"), append "::"
        elif any(
            [
                search.isdigit() and int(search) > 255,
                self.RE_HEXTET.match(search),
            ]
        ):
            search += "::"

        return search

    def parse_network_string(self, search):
        """
        Attempts to parse a (potentially incomplete) IPAddress and return an IPNetwork.
        eg: '10.10' should be interpreted as netaddr.IPNetwork('10.10.0.0/16')
        """
        version = 4

        # Disregard netmask
        search = search.split("/")[0]

        # We don't want default ambiguous behavior to be IPv6
        if not self._is_ambiguous_network_string(search):
            search = self._check_and_prep_ipv6(search)

        # Attempt to quickly assess v6
        if ":" in search:
            version = 6

        return self._safe_parse_network_string(search, version)

    def parse_ipv6(self, value):
        """IPv6 addresses are 8, 16-bit fields."""

        # Get non-empty octets from search string
        hextets = value.split(":")

        # Before we normalize, check that final value is a digit.
        if hextets[-1].isalnum():
            fill_zeroes = False  # Leave "" in there.
            prefix_len = 128  # Force /128
        # Otherwise fill blanks with zeroes and fuzz prefix_len
        else:
            fill_zeroes = True
            hextets = list(filter(lambda h: h, hextets))
            # Fuzz prefix_len based on parsed octets
            prefix_len = 16 * len(hextets)

        # Replace "" w/ "0"
        if fill_zeroes:
            hextets.extend(["0" for _ in range(len(hextets), 8)])

        # Create an netaddr.IPNetwork to search within
        network = ":".join(hextets)
        ip = f"{network}/{prefix_len}"
        return netaddr.IPNetwork(ip)

    def parse_ipv4(self, value):
        """IPv4 addresses are 4, 8-bit fields."""

        # Get non-empty octets from search string
        octets = value.split(".")
        octets = list(filter(lambda o: o, octets))

        # Fuzz prefix_len based on parsed octets
        prefix_len = 8 * len(octets)

        # Create an netaddr.IPNetwork to search within
        octets.extend(["0" for _ in range(len(octets), 4)])
        network = ".".join(octets)
        ip = f"{network}/{prefix_len}"
        return netaddr.IPNetwork(ip)

    def string_search(self, search):
        """
        Interpret a search string and return useful results.
        """
        if not search:
            return self.none()

        the_filter = Q(description__icontains=search)

        if self._is_ambiguous_network_string(search):
            network = self._safe_parse_network_string(search, 4)  # network becomes always v4 Address in ambiguous case
            last_ip = self._get_last_ip(network)

            network_ip6 = self._safe_parse_network_string(self._check_and_prep_ipv6(search), 6)
            last_ip_ip6 = self._get_last_ip(network_ip6)

            the_filter = the_filter | (
                Q(network__gte=network_ip6.network, broadcast__lte=last_ip_ip6)  # same as `net_contained()`
                | Q(
                    prefix_length__lte=network_ip6.prefixlen,
                    network__lte=network_ip6.network,
                    broadcast__gte=last_ip_ip6,
                )  # same as `net_contains_or_equals()`
            )

        else:
            network = self.parse_network_string(search)  # network may either be v4 or v6 in non-ambiguous case
            last_ip = self._get_last_ip(network)

        the_filter = the_filter | (
            Q(network__gte=network.network, broadcast__lte=last_ip)  # same as `net_contained()`
            | Q(
                prefix_length__lte=network.prefixlen, network__lte=network.network, broadcast__gte=last_ip
            )  # same as `net_contains_or_equals()`
        )

        return self.filter(the_filter)


class PrefixQuerySet(BaseNetworkQuerySet):
    """Queryset for `Prefix` objects."""

    def ip_family(self, family):
        try:
            byte_len = self.ip_family_map[family]
        except KeyError:
            raise ValueError(f"invalid IP family {family}")

        return self.annotate(address_len=Length(F("network"))).filter(address_len=byte_len)

    def net_equals(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        last_ip = self._get_last_ip(prefix)
        return self.filter(prefix_length=prefix.prefixlen, network=prefix.network, broadcast=last_ip)

    def net_contained(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        last_ip = self._get_last_ip(prefix)
        return self.filter(
            prefix_length__gt=prefix.prefixlen,
            network__gte=prefix.network,
            broadcast__lte=last_ip,
        )

    def net_contained_or_equal(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        last_ip = self._get_last_ip(prefix)
        return self.filter(
            prefix_length__gte=prefix.prefixlen,
            network__gte=prefix.network,
            broadcast__lte=last_ip,
        )

    def net_contains(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        last_ip = self._get_last_ip(prefix)
        return self.filter(
            prefix_length__lt=prefix.prefixlen,
            network__lte=prefix.network,
            broadcast__gte=last_ip,
        )

    def net_contains_or_equals(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        last_ip = self._get_last_ip(prefix)
        return self.filter(
            prefix_length__lte=prefix.prefixlen,
            network__lte=prefix.network,
            broadcast__gte=last_ip,
        )

    def get(self, *args, prefix=None, **kwargs):
        """
        Provide a convenience for `.get(prefix=<prefix>)`
        """
        if prefix:
            _prefix = netaddr.IPNetwork(prefix)
            if str(_prefix) != str(prefix):
                raise self.model.DoesNotExist()
            last_ip = self._get_last_ip(_prefix)
            kwargs["prefix_length"] = _prefix.prefixlen
            kwargs["network"] = _prefix.ip  # Query based on the input, not the true network address
            kwargs["broadcast"] = last_ip
        return super().get(*args, **kwargs)

    def filter(self, *args, prefix=None, **kwargs):
        """
        Provide a convenience for `.filter(prefix=<prefix>)`
        """
        if prefix:
            _prefix = netaddr.IPNetwork(prefix)
            last_ip = self._get_last_ip(_prefix)
            kwargs["prefix_length"] = _prefix.prefixlen
            kwargs["network"] = _prefix.ip  # Query based on the input, not the true network address
            kwargs["broadcast"] = last_ip
        return super().filter(*args, **kwargs)

    # TODO(jathan): This was copied from `Prefix.delete()` but this won't work in the same way.
    # Currently the issue is with `queryset.delete()` on bulk delete view from list view, how do we
    # reference the "parent" that was deleted here? It's not in context on the `ProtectedError`.
    # raised. This comment can be deleted after this has been successfully unit-tested.
    def delete(self, *args, **kwargs):
        """
        A Prefix with children will be impossible to delete and raise a `ProtectedError`.

        If a Prefix has children, this catch the error and explicitly update the
        `protected_objects` from the exception setting their parent to the old parent of this
        prefix, and then this prefix will be deleted.
        """

        try:
            return super().delete(*args, **kwargs)
        except ProtectedError as err:
            # This will be either IPAddress or Prefix.
            protected_instance = tuple(err.protected_objects)[0]
            protected_model = protected_instance._meta.model
            protected_parent = protected_instance.parent
            new_parent = protected_parent.parent_id

            # Prepare a queryset for the protected objects.
            protected_pks = (po.pk for po in err.protected_objects)
            protected_objects = protected_model.objects.filter(pk__in=protected_pks)

            # IPAddress objects must have a parent.
            if protected_model._meta.model_name == "ipaddress" and new_parent is None:
                # If any of the child IPs would have a null parent after this change, raise an
                # error.
                raise ProtectedError(
                    msg=(
                        f"Cannot delete Prefix {protected_parent} because it has child IPAddress"
                        " objects that would no longer have a parent."
                    ),
                    protected_objects=err.protected_objects,
                ) from err

            # Update protected objects to use grand-parent of the parent Prefix and delete the old
            # parent. This should be equivalent at the row level of saying `parent=self.parent`.
            protected_objects.update(parent=new_parent)
            return super().delete(*args, **kwargs)

    def _validate_cidr(self, value):
        """
        Validate whether `value` is a validr IPv4/IPv6 CIDR.

        Args:
            value (str): IP address
        """
        try:
            return netaddr.IPNetwork(str(value))
        except netaddr.AddrFormatError as err:
            raise ValidationError({"cidr": f"{value} does not appear to be an IPv4 or IPv6 network."}) from err

    def get_closest_parent(self, cidr, namespace, max_prefix_length=0):
        """
        Return the closest matching parent Prefix for a `cidr` even if it doesn't exist in the database.

        Args:
            cidr (str): IPv4/IPv6 CIDR string
            namespace (Namespace): Namespace instance
            max_prefix_length (int): Maximum prefix length depth for closest parent lookup
        """
        # Validate that it's a real CIDR
        cidr = self._validate_cidr(cidr)
        broadcast = str(cidr.broadcast or cidr.ip)
        ip_version = cidr.version

        try:
            max_prefix_length = int(max_prefix_length)
        except ValueError:
            raise ValidationError({"max_prefix_length": f"Invalid prefix_length: {max_prefix_length}."})

        # Walk the supernets backwrds from smallest to largest prefix.
        try:
            supernets = cidr.supernet(prefixlen=max_prefix_length)
        except ValueError as err:
            raise ValidationError({"max_prefix_length": str(err)})
        else:
            supernets.reverse()

        # Enumerate all unique networks and prefixes
        networks = {str(s.network) for s in supernets}
        del supernets  # Free the memory because it could be quite large.

        # Prepare the queryset filter
        lookup_kwargs = {
            "network__in": networks,
            # TODO(jathan): This might be flawed if an IPAddress has a prefix_length that excludes it from a
            # parent that should otherwise contain it. If we encounter issues in the future for
            # identifying closest parent prefixes, this might be a starting point.
            "prefix_length__lte": cidr.prefixlen,
            "broadcast__gte": broadcast,
            "ip_version": ip_version,
            "namespace": namespace,
        }

        # Search for possible ancestors by network/prefix, returning them in reverse order, so that
        # we can choose the first one.
        possible_ancestors = self.filter(**lookup_kwargs).order_by("-prefix_length")

        # If we've got any matches, the first one is our closest parent.
        try:
            return possible_ancestors[0]
        except IndexError:
            raise self.model.DoesNotExist(f"Could not determine parent Prefix for {cidr}")


class IPAddressQuerySet(BaseNetworkQuerySet):
    """Queryset for `IPAddress` objects."""

    def get_queryset(self):
        """
        By default, PostgreSQL will order INETs with shorter (larger) prefix lengths ahead of those with longer
        (smaller) masks. This makes no sense when ordering IPs, which should be ordered solely by family and host
        address. We can use HOST() to extract just the host portion of the address (ignoring its mask), but we must
        then re-cast this value to INET() so that records will be ordered properly. We are essentially re-casting each
        IP address as a /32 or /128.
        """
        return super().order_by("host")

    def ip_family(self, family):
        try:
            byte_len = self.ip_family_map[family]
        except KeyError:
            raise ValueError(f"invalid IP family {family}")

        return self.annotate(address_len=Length(F("host"))).filter(address_len=byte_len)

    def string_search(self, search):
        """
        Interpret a search string and return useful results.
        """
        if not search:
            return self.none()

        the_filter = Q(dns_name__icontains=search) | Q(description__icontains=search)

        if self._is_ambiguous_network_string(search):
            network = self._safe_parse_network_string(search, 4)  # network becomes always v4 Address in ambiguous case
            last_ip = self._get_last_ip(network)

            network_ip6 = self._safe_parse_network_string(self._check_and_prep_ipv6(search), 6)
            last_ip_ip6 = self._get_last_ip(network_ip6)

            the_filter |= Q(host__lte=last_ip_ip6, host__gte=network_ip6.network)  # same as `net_host_contained()`

        else:
            network = self.parse_network_string(search)  # network may either be v4 or v6 in non-ambiguous case
            last_ip = self._get_last_ip(network)

        the_filter |= Q(host__lte=last_ip, host__gte=network.network)  # same as `net_host_contained()`

        return self.filter(the_filter)

    def net_host_contained(self, network):
        # consider only host ip address when
        # filtering for membership in |network|
        network = netaddr.IPNetwork(network)
        last_ip = self._get_last_ip(network)
        return self.filter(
            host__lte=last_ip,
            host__gte=network.network,
        )

    def net_in(self, networks):
        # for a tuple of IP addresses, filter queryset for matches.
        # values may or may not have netmasks: ['10.0.0.1', '10.0.0.1/24', '10.0.0.1/25']
        masked_hosts = [bytes(netaddr.IPNetwork(val).ip) for val in networks if "/" in val]
        masked_prefixes = [netaddr.IPNetwork(val).prefixlen for val in networks if "/" in val]
        unmasked_hosts = [bytes(netaddr.IPNetwork(val).ip) for val in networks if "/" not in val]
        return self.filter(Q(host__in=masked_hosts, mask_length__in=masked_prefixes) | Q(host__in=unmasked_hosts))

    def get(self, *args, address=None, **kwargs):
        """
        Provide a convenience for `.get(address=<address>)`
        """
        if address:
            address = netaddr.IPNetwork(address)
            kwargs["mask_length"] = address.prefixlen
            kwargs["host"] = address.ip
        return super().get(*args, **kwargs)

    def filter(self, *args, address=None, **kwargs):
        """
        Provide a convenience for `.filter(address=<address>)`
        """
        if address:
            address = netaddr.IPNetwork(address)
            kwargs["mask_length"] = address.prefixlen
            kwargs["host"] = address.ip
        return super().filter(*args, **kwargs)

    def filter_address_or_pk_in(self, addresses, pk_values=None):
        """
        Filters by a list of address and or pk

        Similar to .filter(address__in=[<address>]`)
        """
        q = Q()
        for _address in addresses:
            _address = netaddr.IPNetwork(_address)
            mask_length = _address.prefixlen
            host = _address.ip
            q |= Q(mask_length=mask_length, host=host)

        if pk_values is not None:
            q |= Q(pk__in=pk_values)

        return super().filter(q)
