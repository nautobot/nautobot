"""Test IPAM forms."""

from django.test import TestCase

from nautobot.dcim.models import Device, DeviceType, DeviceRole, Interface, Manufacturer, Site
from nautobot.extras.models.statuses import Status
from nautobot.ipam import forms, models


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

        self.assertFalse(form.is_valid())
        self.assertEqual(f"Cannot create {self.object_name} with /0 mask.", form.errors[self.field_name][0])

    def test_address_missing_mask(self):
        data = {self.field_name: "192.168.0.1"}
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
        self.extra_data = {"rir": models.RIR.objects.first()}


class PrefixFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.PrefixForm
    field_name = "prefix"
    object_name = "prefix"

    def setUp(self):
        super().setUp()
        self.extra_data = {"status": Status.objects.get(slug="active")}


class IPAddressFormTest(BaseNetworkFormTest, TestCase):
    form_class = forms.IPAddressForm
    field_name = "address"
    object_name = "IP address"

    def setUp(self):
        super().setUp()
        self.extra_data = {"status": Status.objects.get(slug="active")}

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

    def test_primary_ip_not_altered_if_adding_a_new_IP_to_diff_interface(self):
        """Test primary IP of a device is not lost when adding a new IP to a different interface."""
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(model="Device Type 1", slug="device-type-1", manufacturer=manufacturer)
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        status_active = Status.objects.get_for_model(Device).get(slug="active")
        site = Site.objects.first()
        device = Device.objects.create(
            name="Device 1",
            site=site,
            device_type=devicetype,
            device_role=devicerole,
            status=status_active,
        )
        interface1 = Interface.objects.create(device=device, name="eth0")
        interface2 = Interface.objects.create(device=device, name="eth1")

        ipaddress1 = "191.168.0.5/32"
        ipaddress2 = "192.168.0.5/32"

        form1 = self.form_class(
            data={
                self.field_name: ipaddress1,
                "status": Status.objects.get(slug="active"),
                "device": device,
                "interface": interface1,
                "primary_for_parent": True,
            }
        )
        form1.is_valid()
        form1.save()

        form2 = self.form_class(
            data={
                self.field_name: ipaddress2,
                "status": Status.objects.get(slug="active"),
                "device": device,
                "interface": interface2,
            }
        )

        form2.is_valid()
        form2.save()

        device.refresh_from_db()
        # Assert primary IP was not altered
        self.assertEqual(str(device.primary_ip4), ipaddress1)
