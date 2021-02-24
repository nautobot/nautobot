import uuid

import netaddr
from django.db.models import ExpressionWrapper, IntegerField, F, QuerySet, Q
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Length

from nautobot.ipam.constants import IPV4_BYTE_LENGTH, IPV6_BYTE_LENGTH
from nautobot.utilities.querysets import RestrictedQuerySet


class NetworkQuerySet(QuerySet):

    def net_equals(self, prefix):
        return self.filter(
            prefix_length=prefix.prefixlen,
            network=bytes(prefix.network),
            broadcast=bytes(prefix.broadcast),
        )

    def net_contained(self, prefix):
        return self.filter(
            prefix_length__gt=prefix.prefixlen,
            network__gte=bytes(prefix.network),
            broadcast__lte=bytes(prefix.broadcast),
        )

    def net_contained_or_equal(self, prefix):
        return self.filter(
            prefix_length__gte=prefix.prefixlen,
            network__gte=bytes(prefix.network),
            broadcast__lte=bytes(prefix.broadcast),
        )

    def net_contains(self, prefix):
        return self.filter(
            prefix_length__lt=prefix.prefixlen,
            network__lte=bytes(prefix.network),
            broadcast__gte=bytes(prefix.broadcast)
        )

    def net_contains_or_equal(self, prefix):
        return self.filter(
            prefix_length__lte=prefix.prefixlen,
            network__lte=bytes(prefix.network),
            broadcast__gte=bytes(prefix.broadcast)
        )


class AggregateQuerySet(NetworkQuerySet, RestrictedQuerySet):
    pass


class PrefixQuerySet(NetworkQuerySet, RestrictedQuerySet):
    def annotate_tree(self):
        """
        Annotate the number of parent and child prefixes for each Prefix. Raw SQL is needed for these subqueries
        because we need to cast NULL VRF values to UUID for comparison. (NULL != NULL).

        The UUID being used is fake.
        """
        # The COALESCE needs a valid, non-zero, non-null UUID value to do the comparison.
        # The value itself has no meaning, so we just generate a random UUID for the query.
        FAKE_UUID = uuid.uuid4()

        qs = self.annotate(maybe_vrf=ExpressionWrapper(
            Coalesce(F('vrf_id'), FAKE_UUID),
            output_field=IntegerField()
        ))

        return qs.annotate(
            parents=RawSQL(
                'SELECT COUNT(*) FROM ipam_prefix AS U0 '
               'WHERE U0.prefix_length < ipam_prefix.prefix_length '
               'AND U0.network <= ipam_prefix.network '
               'AND U0.broadcast >= ipam_prefix.broadcast '
               f'AND COALESCE(U0.vrf_id, \'{FAKE_UUID}\') >= COALESCE(ipam_prefix.vrf_id, \'{FAKE_UUID}\')', ()
            ),
            children=RawSQL(
                'SELECT COUNT(*) FROM ipam_prefix AS U1 '
                'WHERE U1.prefix_length = ipam_prefix.prefix_length '
                'AND U1.network >= ipam_prefix.network '
                'AND U1.broadcast <= ipam_prefix.broadcast '
                f'AND COALESCE(U1.vrf_id, \'{FAKE_UUID}\') <= COALESCE(ipam_prefix.vrf_id, \'{FAKE_UUID}\')', ()
            ),
        )


class IPAddressQuerySet(RestrictedQuerySet):
    ip_family_map = {
        4: IPV4_BYTE_LENGTH,
        6: IPV6_BYTE_LENGTH,
    }

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
            raise ValueError('invalid IP family {}'.format(family))

        return self.annotate(
            address_len=Length(F('host'))
        ).filter(
            address_len=byte_len
        )

    def net_host_contained(self, network):
        return self.filter(
            host__lte=bytes(network.broadcast),
            host__gte=bytes(network.network),
        )

    def net_contained_or_equal(self, network):
        return self.filter(
            host__lte=bytes(network.broadcast),
            host__gte=bytes(network.host),
        )

    def net_in(self, networks):
        # for a tuple of IP addresses, filter queryset for matches.
        # values may or may not have netmasks: ['10.0.0.1', '10.0.0.1/24', '10.0.0.1/25']
        masked_hosts = [bytes(netaddr.IPNetwork(val).ip) for val in networks if '/' in val]
        masked_prefixes = [netaddr.IPNetwork(val).prefixlen for val in networks if '/' in val]
        unmasked_hosts = [bytes(netaddr.IPNetwork(val).ip) for val in networks if '/' not in val]
        return self.filter(
            Q(host__in=masked_hosts,
              prefix_length__in=masked_prefixes) |
            Q(host__in=unmasked_hosts)
        )