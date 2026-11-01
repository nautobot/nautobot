from nautobot.cloud.models import CloudNetwork
from nautobot.core.testing import TestCase
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, Prefix


class IPAddressQuerySet(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        cls.ipaddr_status = Status.objects.get_for_model(IPAddress).first()

        cls.prefix = Prefix.objects.create(prefix="10.0.0.0/8", status=cls.prefix_status)
        cls.ip_address = IPAddress.objects.create(address="10.0.0.1/32", status=cls.ipaddr_status)

    def test_net_contains_or_equals_in_subquery(self):
        self.assertIsNone(
            CloudNetwork.objects.filter(
                prefixes=Prefix.objects.filter(network__net_contains_or_equals=self.ip_address.host)
            ).first(),
        )

    def test_net_in_in_subquery(self):
        self.assertIsNone(
            CloudNetwork.objects.filter(
                prefixes__in=IPAddress.objects.filter(host__net_in=[Prefix.objects.first().network]).values("parent")
            ).first(),
        )

    def test_host(self):
        self.assertIsNone(
            CloudNetwork.objects.filter(
                prefixes__in=IPAddress.objects.filter(host__net_host=Prefix.objects.first().network).values("parent")
            ).first()
        )
