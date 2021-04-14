"""Test IPAM forms."""
from django.test import TestCase

from nautobot.extras.models.statuses import Status
from nautobot.ipam.forms import IPAddressForm


class EoxFormTest(TestCase):
    def test_valid_ip_address(self):
        form = IPAddressForm(data={"address": "192.168.1.0/24", "status": Status.objects.get(slug="dhcp")})
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_slaac_valid_ipv6(self):
        form = IPAddressForm(
            data={"address": "2001:0db8:0000:0000:0000:ff00:0042:8329/128", "status": Status.objects.get(slug="slaac")}
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
