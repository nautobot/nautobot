import re
import uuid

import netaddr
from django.db.models import (
    Count,
    ExpressionWrapper,
    IntegerField,
    F,
    OuterRef,
    Subquery,
    Q,
    QuerySet,
    UUIDField,
    Value,
)
from django.db.models.functions import Coalesce, Length

from nautobot.ipam.constants import IPV4_BYTE_LENGTH, IPV6_BYTE_LENGTH
from nautobot.utilities.querysets import RestrictedQuerySet


class BaseNetworkQuerySet(RestrictedQuerySet):
    """Base class for network-related querysets."""

    ip_family_map = {
        4: IPV4_BYTE_LENGTH,
        6: IPV6_BYTE_LENGTH,
    }

    # Match string with ending in "::"
    RE_COLON = re.compile(".*::$")

    # Match string from "0000" to "ffff" with no trailing ":"
    RE_HEXTET = re.compile("^[a-f0-9]{4}$")

    @staticmethod
    def _get_last_ip(network):
        """
        Get the last IP address in the given network.

        This is distinct from network.broadcast in the case of point-to-point or host networks
        (neither of which technically have a "broadcast" address).
        """
        return network.broadcast if network.broadcast else network[-1]

    def parse_network_string(self, search):
        """
        Attempts to parse a (potentially incomplete) IPAddress and return an IPNetwork.
        eg: '10.10' should be interpreted as netaddr.IPNetwork('10.10.0.0/16')
        """
        version = 4

        try:
            # Disregard netmask
            search = search.split("/")[0]

            # Attempt to quickly assess v6
            if ":" in search:
                version = 6

            # (IPv6) If the value ends with ":" but it's not "::", make it so.
            if search.endswith(":") and not self.RE_COLON.match(search):
                search += ":"
            # (IPv6) If the value has a colon in it, but doesn't end with one or
            # contain "::"
            elif all(
                [
                    not search.endswith(":"),
                    version == 6,
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
                version = 6

            call_map = {
                4: self.parse_ipv4,
                6: self.parse_ipv6,
            }
            return call_map[version](search)

        except netaddr.core.AddrFormatError:
            ver_map = {4: "0/32", 6: "::/128"}
            return netaddr.IPNetwork(ver_map[version])

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

        network = self.parse_network_string(search)
        last_ip = self._get_last_ip(network)

        return self.filter(
            Q(description__icontains=search)
            | Q(network__gte=network.network, broadcast__lte=last_ip)  # same as `net_contained()`
            | Q(
                prefix_length__lte=network.prefixlen, network__lte=network.network, broadcast__gte=last_ip
            )  # same as `net_contains_or_equals()`
        )


class NetworkQuerySet(BaseNetworkQuerySet):
    """Base class for Prefix/Aggregate querysets."""

    def ip_family(self, family):
        try:
            byte_len = self.ip_family_map[family]
        except KeyError:
            raise ValueError("invalid IP family {}".format(family))

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
            if str(_prefix) != prefix:
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


class AggregateQuerySet(NetworkQuerySet):
    """Queryset for `Aggregate` objects."""


class PrefixQuerySet(NetworkQuerySet):
    """Queryset for `Prefix` objects."""

    def annotate_tree(self):
        """
        Annotate the number of parent and child prefixes for each Prefix.

        The UUID being used is fake for purposes of satisfying the COALESCE condition.
        """
        # The COALESCE needs a valid, non-zero, non-null UUID value to do the comparison.
        # The value itself has no meaning, so we just generate a random UUID for the query.
        FAKE_UUID = uuid.uuid4()

        from nautobot.ipam.models import Prefix

        return self.annotate(
            parents=Subquery(
                Prefix.objects.annotate(
                    maybe_vrf=ExpressionWrapper(
                        Coalesce(F("vrf_id"), FAKE_UUID),
                        output_field=UUIDField(),
                    )
                )
                .filter(
                    Q(prefix_length__lt=OuterRef("prefix_length"))
                    & Q(network__lte=OuterRef("network"))
                    & Q(broadcast__gte=OuterRef("broadcast"))
                    & Q(
                        maybe_vrf=ExpressionWrapper(
                            Coalesce(OuterRef("vrf_id"), FAKE_UUID),
                            output_field=UUIDField(),
                        )
                    )
                )
                .order_by()
                .annotate(dummy_group_by=Value(1))  # This is an ORM hack to remove the unwanted GROUP BY clause
                .values("dummy_group_by")
                .annotate(count=Count("*"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
            children=Subquery(
                Prefix.objects.annotate(
                    maybe_vrf=ExpressionWrapper(
                        Coalesce(F("vrf_id"), FAKE_UUID),
                        output_field=UUIDField(),
                    )
                )
                .filter(
                    Q(prefix_length__gt=OuterRef("prefix_length"))
                    & Q(network__gte=OuterRef("network"))
                    & Q(broadcast__lte=OuterRef("broadcast"))
                    & Q(
                        maybe_vrf=ExpressionWrapper(
                            Coalesce(OuterRef("vrf_id"), FAKE_UUID),
                            output_field=UUIDField(),
                        )
                    )
                )
                .order_by()
                .annotate(dummy_group_by=Value(1))  # This is an ORM hack to remove the unwanted GROUP BY clause
                .values("dummy_group_by")
                .annotate(count=Count("*"))
                .values("count")[:1],
                output_field=IntegerField(),
            ),
        )


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
            raise ValueError("invalid IP family {}".format(family))

        return self.annotate(address_len=Length(F("host"))).filter(address_len=byte_len)

    def string_search(self, search):
        """
        Interpret a search string and return useful results.
        """
        if not search:
            return self.none()

        network = self.parse_network_string(search)
        last_ip = self._get_last_ip(network)
        return self.filter(
            Q(dns_name__icontains=search)
            | Q(description__icontains=search)
            | Q(host__lte=last_ip, host__gte=network.network)  # same as `net_host_contained()`
        )

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
        return self.filter(Q(host__in=masked_hosts, prefix_length__in=masked_prefixes) | Q(host__in=unmasked_hosts))

    def get(self, *args, address=None, **kwargs):
        """
        Provide a convenience for `.get(address=<address>)`
        """
        if address:
            address = netaddr.IPNetwork(address)
            last_ip = self._get_last_ip(address)
            kwargs["prefix_length"] = address.prefixlen
            kwargs["host"] = address.ip
            kwargs["broadcast"] = last_ip
        return super().get(*args, **kwargs)

    def filter(self, *args, address=None, **kwargs):
        """
        Provide a convenience for `.filter(address=<address>)`
        """
        if address:
            address = netaddr.IPNetwork(address)
            last_ip = self._get_last_ip(address)
            kwargs["prefix_length"] = address.prefixlen
            kwargs["host"] = address.ip
            kwargs["broadcast"] = last_ip
        return super().filter(*args, **kwargs)
