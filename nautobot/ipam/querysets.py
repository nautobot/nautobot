import uuid

from nautobot.utilities.querysets import RestrictedQuerySet


class PrefixQuerySet(RestrictedQuerySet):
    def annotate_tree(self):
        """
        Annotate the number of parent and child prefixes for each Prefix. Raw SQL is needed for these subqueries
        because we need to cast NULL VRF values to UUID for comparison. (NULL != NULL).

        The UUID being used is fake.
        """
        # The COALESCE needs a valid, non-zero, non-null UUID value to do the comparison.
        # The value itself has no meaning, so we just generate a random UUID for the query.
        FAKE_UUID = uuid.uuid4()
        return self.extra(
            select={
                "parents": 'SELECT COUNT(U0."prefix") AS "c" '
                'FROM "ipam_prefix" U0 '
                'WHERE (U0."prefix" >> "ipam_prefix"."prefix" '
                f'AND COALESCE(U0."vrf_id", \'{FAKE_UUID}\') = COALESCE("ipam_prefix"."vrf_id", \'{FAKE_UUID}\'))',
                "children": 'SELECT COUNT(U1."prefix") AS "c" '
                'FROM "ipam_prefix" U1 '
                'WHERE (U1."prefix" << "ipam_prefix"."prefix" '
                f'AND COALESCE(U1."vrf_id", \'{FAKE_UUID}\') = COALESCE("ipam_prefix"."vrf_id", \'{FAKE_UUID}\'))',
            }
        )
