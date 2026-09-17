from nautobot.core import testing
from nautobot.extras.models import Status
from nautobot.ipam import factory, models
from nautobot.ipam.choices import PrefixTypeChoices


class IPAddressRangeFactoryTestCase(testing.TestCase):
    """Tests for IPAddressRangeFactory."""

    def test_factory_creates_valid_range(self):
        """A created range is contained within its parent and has start <= end."""
        rng = factory.IPAddressRangeFactory.create()

        self.assertIsNotNone(rng.parent)
        self.assertLessEqual(rng.start_address, rng.end_address)
        parent_net = rng.parent.prefix
        self.assertGreaterEqual(int(rng.start_address), parent_net.first)
        self.assertLessEqual(int(rng.end_address), parent_net.last)
        self.assertEqual(rng.ip_version, rng.start_address.version)

    def test_factory_can_create_ipv6_range(self):
        """The factory can carve a range from an IPv6 parent prefix."""
        from nautobot.ipam.models import Namespace

        namespace = Namespace.objects.first()
        prefix_status = Status.objects.get_for_model(models.Prefix).first()
        parent = models.Prefix.objects.create(
            prefix="2001:db8:abcd:50::/64",
            type=PrefixTypeChoices.TYPE_NETWORK,
            namespace=namespace,
            status=prefix_status,
        )

        rng = factory.IPAddressRangeFactory.create(parent=parent)

        self.assertEqual(rng.ip_version, 6)
        self.assertEqual(rng.parent, parent)
        self.assertLessEqual(rng.start_address, rng.end_address)

    def test_factory_exclusive_range_never_conflicts(self):
        """is_exclusive only commits to True when the carved span has no IPAddress.

        This is the self-protecting behavior: an exclusive range that overlapped an
        existing IP would fail _validate_no_exclusive_ip_conflict, so a successfully
        created exclusive range must have an empty span.
        """
        ranges = factory.IPAddressRangeFactory.create_batch(15)

        for rng in ranges:
            if rng.is_exclusive:
                conflicting = models.IPAddress.objects.filter(
                    parent=rng.parent,
                    host__gte=rng.start_host,
                    host__lte=rng.end_host,
                ).exists()
                self.assertFalse(
                    conflicting,
                    f"Exclusive range {rng} overlaps an existing IPAddress",
                )

    def test_factory_batch_creates_distinct_ranges(self):
        """create_batch reliably yields the requested number of ranges."""
        ranges = factory.IPAddressRangeFactory.create_batch(10)

        self.assertEqual(len(ranges), 10)
        self.assertEqual(len({r.pk for r in ranges}), 10)
