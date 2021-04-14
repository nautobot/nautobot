"""Test IPAM forms."""
from django.test import TestCase

from nautobot.extras.models.statuses import Status
from nautobot.ipam.forms import IPAddressForm


class IPAddressFormTest(TestCase):
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

    def test_slaac_status_invalid_ipv4(self):
        form = IPAddressForm(data={"address": "192.168.0.1/32", "status": Status.objects.get(slug="slaac")})
        self.assertFalse(form.is_valid())
        self.assertEquals("Only IPv6 addresses can be assigned SLAAC status", form.errors["status"])

    def test_address_invalid_ipv4(self):
        form = IPAddressForm(data={"address": "192.168.0.1/64", "status": Status.objects.get(slug="dhcp")})
        self.assertFalse(form.is_valid())
        self.assertIn("Please specify a valid IPv4 or IPv6 address.", form.errors)

    def test_address_missing_cidr_mask(self):
        form = IPAddressForm(data={"address": "192.168.0.1/0", "status": Status.objects.get(slug="dhcp")})
        self.assertFalse(form.is_valid())
        self.assertIn("CIDR mask (e.g. /24) is required.", form.errors)
