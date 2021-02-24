import uuid

from django.db.models import ExpressionWrapper, IntegerField, F, QuerySet
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce

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
