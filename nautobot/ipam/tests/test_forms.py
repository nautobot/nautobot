"""Test IPAM forms."""
from unittest import skip

from django.test import TestCase

from nautobot.extras.models import Status
from nautobot.ipam import forms, models
from nautobot.ipam.choices import IPAddressStatusChoices
from nautobot.ipam.models import IPAddress, Prefix


class BaseNetworkFormTest:
    form_class = None
    field_name = None
    object_name = None
    extra_data = {}

    def test_valid_ip_address(self):
        data = {self.field_name: "192.168.1.0/24"}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_address_invalid_ipv4(self):
        data = {self.field_name: "192.168.0.1/64"}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertFalse(form.is_valid())
        self.assertEqual("Please specify a valid IPv4 or IPv6 address.", form.errors[self.field_name][0])

    def test_address_zero_mask(self):
        data = {self.field_name: "192.168.0.1/0"}
        data.update(self.extra_data)
        form = self.form_class(data)

        # With the advent of `Prefix.parent`, it's now possible to create a /0 .
        self.assertTrue(form.is_valid())

    def test_address_missing_mask(self):
        data = {self.field_name: "192.168.0.1"}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertFalse(form.is_valid())
        self.assertEqual("CIDR mask (e.g. /24) is required.", form.errors[self.field_name][0])


@skip("Needs to be updated for Namespaces")
class PrefixFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.PrefixForm
    field_name = "prefix"
    object_name = "prefix"

    def setUp(self):
        super().setUp()
        self.extra_data = {
            "status": Status.objects.get_for_model(Prefix).first(),
            "type": "network",
            "rir": models.RIR.objects.first(),
        }


@skip("Needs to be updated for Namespaces")
class IPAddressFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.IPAddressForm
    field_name = "address"
    object_name = "IP address"

    def setUp(self):
        super().setUp()
        self.extra_data = {"status": Status.objects.get_for_model(IPAddress).first()}

    def test_slaac_valid_ipv6(self):
        form = self.form_class(
            data={
                self.field_name: "2001:0db8:0000:0000:0000:ff00:0042:8329/128",
                "status": Status.objects.get(name="SLAAC"),
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_slaac_status_invalid_ipv4(self):
        slaac = IPAddressStatusChoices.as_dict()[IPAddressStatusChoices.STATUS_SLAAC]
        form = self.form_class(data={self.field_name: "192.168.0.1/32", "status": Status.objects.get(name=slaac)})
        self.assertFalse(form.is_valid())
        self.assertEqual("Only IPv6 addresses can be assigned SLAAC status", form.errors["status"][0])
