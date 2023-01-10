"""Test IPAM forms."""
from unittest import mock

from django.test import TestCase
from netaddr import IPNetwork

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Site
from nautobot.extras.models.statuses import Status
from nautobot.ipam import forms, models as ipam_models
from nautobot.ipam.forms import mixins


class AddressFieldMixinTest(TestCase):
    """Test cases for the AddressFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the AddressFieldMixin."""
        self.ip = ipam_models.IPAddress.objects.create(address="10.0.0.1/24")
        self.initial = {"address": self.ip.address}

    def test_address_initial(self):
        """Ensure initial kwargs for address is passed in."""
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            ip_none = ipam_models.IPAddress()
            mixins.AddressFieldMixin(initial=self.initial, instance=ip_none)
            mock_init.assert_called_with(initial=self.initial, instance=ip_none)

    def test_address_instance(self):
        """Ensure override with computed field when initial kwargs for address is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.core.forms.forms
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            mixins.AddressFieldMixin(instance=self.ip)
            mock_init.assert_called_with(initial=self.initial, instance=self.ip)


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


class PrefixFieldMixinTest(TestCase):
    """Test cases for the PrefixFieldMixin."""

    def setUp(self):
        """Setting up shared variables for the PrefixFieldMixin."""
        self.prefix = ipam_models.Prefix.objects.create(prefix=IPNetwork("10.0.0.0/24"))
        self.initial = {"prefix": self.prefix.prefix}

    def test_prefix_initial(self):
        """Ensure initial kwargs for prefix is passed through."""
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            prefix_none = ipam_models.Prefix()
            mixins.PrefixFieldMixin(initial=self.initial, instance=prefix_none)
            mock_init.assert_called_with(initial=self.initial, instance=prefix_none)

    def test_prefix_instance(self):
        """Ensure override with computed field when initial kwargs for prefix is not passed in."""

        # Mock the django.forms.ModelForm __init__ function used in nautobot.core.forms.forms
        with mock.patch("nautobot.core.forms.forms.forms.ModelForm.__init__") as mock_init:
            mixins.PrefixFieldMixin(instance=self.prefix)
            mock_init.assert_called_with(initial=self.initial, instance=self.prefix)


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
