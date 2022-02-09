"""Test IPAM forms."""

from django.test import TestCase

from nautobot.extras.models.statuses import Status
from nautobot.ipam import forms, models


class BaseNetworkFormTest:
    form_class = None
    field_name = None
    object_name = None
    extra_data = {}

    def test_valid_ip_address(self):
        data = {self.field_name: "192.168.1.0/24", "status": Status.objects.get(slug="active")}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_address_invalid_ipv4(self):
        data = {self.field_name: "192.168.0.1/64", "status": Status.objects.get(slug="active")}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertFalse(form.is_valid())
        self.assertEqual("Please specify a valid IPv4 or IPv6 address.", form.errors[self.field_name][0])

    def test_address_zero_mask(self):
        data = {self.field_name: "192.168.0.1/0", "status": Status.objects.get(slug="active")}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(f"Cannot create {self.object_name} with /0 mask.", form.errors[self.field_name][0])

    def test_address_missing_mask(self):
        data = {self.field_name: "192.168.0.1", "status": Status.objects.get(slug="active")}
        data.update(self.extra_data)
        form = self.form_class(data)

        self.assertFalse(form.is_valid())
        self.assertEqual("CIDR mask (e.g. /24) is required.", form.errors[self.field_name][0])


class AggregateFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.AggregateForm
    field_name = "prefix"
    object_name = "aggregate"

    def setUp(self):
        super().setUp()
        self.extra_data = {"rir": models.RIR.objects.create(name="RIR", slug="rir")}


class PrefixFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.PrefixForm
    field_name = "prefix"
    object_name = "prefix"


class IPAddressFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.IPAddressForm
    field_name = "address"
    object_name = "IP address"

    def test_slaac_valid_ipv6(self):
        form = self.form_class(
            data={
                self.field_name: "2001:0db8:0000:0000:0000:ff00:0042:8329/128",
                "status": Status.objects.get(slug="slaac"),
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_slaac_status_invalid_ipv4(self):
        form = self.form_class(data={self.field_name: "192.168.0.1/32", "status": Status.objects.get(slug="slaac")})
        self.assertFalse(form.is_valid())
        self.assertEqual("Only IPv6 addresses can be assigned SLAAC status", form.errors["status"][0])
