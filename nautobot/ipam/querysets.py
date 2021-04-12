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
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Length

from nautobot.ipam.constants import IPV4_BYTE_LENGTH, IPV6_BYTE_LENGTH
from nautobot.utilities.querysets import RestrictedQuerySet


class NetworkQuerySet(QuerySet):
    @staticmethod
    def _get_broadcast(prefix):
        return prefix.broadcast if prefix.broadcast else prefix.network

    def net_equals(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        broadcast = self._get_broadcast(prefix)
        return self.filter(prefix_length=prefix.prefixlen, network=prefix.network, broadcast=broadcast)

    def net_contained(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        broadcast = self._get_broadcast(prefix)
        return self.filter(
            prefix_length__gt=prefix.prefixlen,
            network__gte=prefix.network,
            broadcast__lte=broadcast,
        )

    def net_contained_or_equal(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        broadcast = self._get_broadcast(prefix)
        return self.filter(
            prefix_length__gte=prefix.prefixlen,
            network__gte=prefix.network,
            broadcast__lte=broadcast,
        )

    def net_contains(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        broadcast = self._get_broadcast(prefix)
        return self.filter(
            prefix_length__lt=prefix.prefixlen,
            network__lte=prefix.network,
            broadcast__gte=broadcast,
        )

    def net_contains_or_equals(self, prefix):
        prefix = netaddr.IPNetwork(prefix)
        broadcast = self._get_broadcast(prefix)
        return self.filter(
            prefix_length__lte=prefix.prefixlen,
            network__lte=prefix.network,
            broadcast__gte=broadcast,
        )

    def get(self, *args, prefix=None, **kwargs):
        """
        Provide a convenience for `.get(prefix=<prefix>)`
        """
        if prefix:
            _prefix = netaddr.IPNetwork(prefix)
            if str(_prefix) != prefix:
                raise self.model.DoesNotExist()
            broadcast = self._get_broadcast(_prefix)
            kwargs["prefix_length"] = _prefix.prefixlen
            kwargs["network"] = _prefix.ip  # Query based on the input, not the true network address
            kwargs["broadcast"] = broadcast
        return super().get(*args, **kwargs)

    def filter(self, *args, prefix=None, **kwargs):
        """
        Provide a convenience for `.filter(prefix=<prefix>)`
        """
        if prefix:
            _prefix = netaddr.IPNetwork(prefix)
            broadcast = self._get_broadcast(_prefix)
            kwargs["prefix_length"] = _prefix.prefixlen
            kwargs["network"] = _prefix.ip  # Query based on the input, not the true network address
            kwargs["broadcast"] = broadcast
        return super().filter(*args, **kwargs)


class AggregateQuerySet(NetworkQuerySet, RestrictedQuerySet):
    pass


class PrefixQuerySet(NetworkQuerySet, RestrictedQuerySet):
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


class IPAddressQuerySet(RestrictedQuerySet):
    ip_family_map = {
        4: IPV4_BYTE_LENGTH,
        6: IPV6_BYTE_LENGTH,
    }

    @staticmethod
    def _get_broadcast(network):
        return network.broadcast if network.broadcast else network.network

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

    def net_host_contained(self, network):
        # consider only host ip address when
        # filtering for membership in |network|
        network = netaddr.IPNetwork(network)
        broadcast = self._get_broadcast(network)
        return self.filter(
            host__lte=broadcast,
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
            broadcast = self._get_broadcast(address)
            kwargs["prefix_length"] = address.prefixlen
            kwargs["host"] = address.ip
            kwargs["broadcast"] = broadcast
        return super().get(*args, **kwargs)

    def filter(self, *args, address=None, **kwargs):
        """
        Provide a convenience for `.filter(address=<address>)`
        """
        if address:
            address = netaddr.IPNetwork(address)
            broadcast = self._get_broadcast(address)
            kwargs["prefix_length"] = address.prefixlen
            kwargs["host"] = address.ip
            kwargs["broadcast"] = broadcast
        return super().filter(*args, **kwargs)
