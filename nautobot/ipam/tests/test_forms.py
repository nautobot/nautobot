"""Test IPAM forms."""

from django.forms import Form
from django.test import TestCase

from nautobot.core.testing.forms import FormTestCases
from nautobot.extras.models import Status
from nautobot.ipam import forms, models
from nautobot.ipam.choices import IPAddressTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix


class NetworkFormTestCases:
    class BaseNetworkFormTest(TestCase):
        form_class: type[Form]
        field_name: str
        object_name: str
        extra_data = {}

        def setUp(self):
            super().setUp()
            self.namespace = Namespace.objects.create(name="IPAM Form Test")
            self.status = Status.objects.get(name="Active")
            self.prefix_status = Status.objects.get_for_model(Prefix).first()
            self.ip_status = Status.objects.get_for_model(IPAddress).first()
            self.parent = Prefix.objects.create(
                prefix="192.168.1.0/24", namespace=self.namespace, status=self.prefix_status
            )
            self.parent2 = Prefix.objects.create(
                prefix="192.168.0.0/16", namespace=self.namespace, status=self.prefix_status
            )
            self.parent6 = Prefix.objects.create(
                prefix="2001:0db8::/40", namespace=self.namespace, status=self.prefix_status
            )

        def test_valid_ip_address(self):
            data = {self.field_name: "192.168.2.0/24", "namespace": self.namespace, "status": self.status}
            data.update(self.extra_data)
            form = self.form_class(data)

            self.assertTrue(form.is_valid())
            self.assertTrue(form.save())

        def test_address_invalid_ipv4(self):
            data = {self.field_name: "192.168.0.1/64", "namespace": self.namespace, "status": self.status}
            data.update(self.extra_data)
            form = self.form_class(data)

            self.assertFalse(form.is_valid())
            self.assertEqual("Please specify a valid IPv4 or IPv6 address.", form.errors[self.field_name][0])

        def test_address_zero_mask(self):
            data = {self.field_name: "192.168.0.1/0", "namespace": self.namespace, "status": self.status}
            data.update(self.extra_data)
            form = self.form_class(data)

            # With the advent of `Prefix.parent`, it's now possible to create a /0 .
            self.assertTrue(form.is_valid())

        def test_address_missing_mask(self):
            data = {self.field_name: "192.168.0.1", "namespace": self.namespace, "status": self.status}
            data.update(self.extra_data)
            form = self.form_class(data)

            self.assertFalse(form.is_valid())
            self.assertEqual("CIDR mask (e.g. /24) is required.", form.errors[self.field_name][0])


class PrefixFormTest(NetworkFormTestCases.BaseNetworkFormTest, FormTestCases.BaseFormTestCase):
    form_class = forms.PrefixForm
    field_name = "prefix"
    object_name = "prefix"

    def setUp(self):
        super().setUp()
        self.extra_data = {
            "namespace": self.namespace,
            "status": self.prefix_status,
            "type": "network",
            "rir": models.RIR.objects.first(),
        }


class IPAddressFormTest(NetworkFormTestCases.BaseNetworkFormTest):
    form_class = forms.IPAddressForm
    field_name = "address"
    object_name = "IP address"

    def setUp(self):
        super().setUp()
        self.extra_data = {
            "namespace": self.namespace,
            "status": self.ip_status,
            "type": IPAddressTypeChoices.TYPE_HOST,
        }

    def test_slaac_valid_ipv6(self):
        data = self.extra_data
        data.update(
            {
                self.field_name: "2001:0db8:0000:0000:0000:ff00:0042:8329/128",
                "type": IPAddressTypeChoices.TYPE_SLAAC,
            }
        )
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_slaac_status_invalid_ipv4(self):
        data = self.extra_data
        data.update(
            {
                self.field_name: "192.168.0.1/32",
                "type": IPAddressTypeChoices.TYPE_SLAAC,
            }
        )
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual("Only IPv6 addresses can be assigned SLAAC type", form.errors["type"][0])


class IPAddressBulkCreateFormTest(TestCase):
    def test_ipaddress_bulk_create_form_pattern_field(self):
        form_class = forms.IPAddressBulkCreateForm
        with self.subTest("Assert IPAddressBulkCreateForm catches address without CIDR mask"):
            form = form_class(data={"pattern": "192.0.2.1"})
            self.assertFalse(form.is_valid())
            self.assertEqual(
                form.errors.get_json_data()["pattern"],
                [{"message": "CIDR mask (e.g. /24) is required.", "code": ""}],
            )
        with self.subTest("Assert IPAddressBulkCreateForm with valid pattern"):
            form = form_class(data={"pattern": "192.0.2.[1,5,100-254]/24"})
            self.assertTrue(form.is_valid())
