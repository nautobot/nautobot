"""Regressions for UI creation transaction failures."""

from unittest.mock import patch

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from nautobot.dcim.forms import InterfaceForm
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleType,
)
from nautobot.extras.models import Role, Status
from nautobot.ipam.forms import IPAddressBulkAddForm
from nautobot.ipam.models import IPAddress, Namespace, Prefix


class UICreationTransactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="input-error-tests", is_superuser=True)
        cls.status = Status.objects.create(name="Input error test status")
        for model in (Device, Interface, Location, Module, IPAddress, Prefix):
            cls.status.content_types.add(ContentType.objects.get_for_model(model))
        role = Role.objects.create(name="Input error test role")
        role.content_types.add(ContentType.objects.get_for_model(Device))
        location_type = LocationType.objects.create(name="Input error test location type")
        location_type.content_types.add(ContentType.objects.get_for_model(Device))
        location = Location.objects.create(
            name="Input error test location", location_type=location_type, status=cls.status
        )
        manufacturer = Manufacturer.objects.create(name="Input error test manufacturer")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Input error test device")
        cls.device = Device.objects.create(
            name="Input error test device", device_type=device_type, location=location, status=cls.status, role=role
        )
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Input error test module")
        module_bay = ModuleBay.objects.create(parent_device=cls.device, name="Input error test bay")
        cls.module = Module.objects.create(module_type=module_type, parent_module_bay=module_bay, status=cls.status)
        cls.interface = Interface.objects.create(
            device=cls.device, name="existing", type="virtual", status=cls.status, mac_address="00:11:22:33:44:55"
        )
        cls.module_interface = Interface.objects.create(
            module=cls.module, name="existing", type="virtual", status=cls.status
        )
        namespace = Namespace.objects.create(name="Input error test namespace")
        prefix = Prefix.objects.create(prefix="192.0.2.0/24", namespace=namespace, status=cls.status)
        cls.ip = IPAddress.objects.create(address="192.0.2.1/24", parent=prefix, status=cls.status)

    def setUp(self):
        self.client = Client(HTTP_HOST="nautobot.example.com")
        self.client.force_login(self.user)

    def component_request(self, parent, pattern):
        return reverse(f"dcim:{parent._meta.model_name}_bulk_add_interface"), {
            "pk": [str(parent.pk)],
            "_create": "",
            "name_pattern": pattern,
            "type": "virtual",
            "status": str(self.status.pk),
        }

    def assert_no_success_message(self, response):
        self.assertFalse(
            any(message.level == messages.SUCCESS for message in messages.get_messages(response.wsgi_request))
        )

    def test_component_database_failure_is_not_reported_as_success(self):
        self.client.raise_request_exception = False
        original_save = InterfaceForm.save

        def save(form, *args, **kwargs):
            # Simulate a uniqueness conflict after form validation. Leave the
            # actual database constraint enabled and let the first INSERT succeed.
            if form.instance.name == "new2":
                form.instance.name = "existing"
            return original_save(form, *args, **kwargs)

        for parent in (self.device, self.module):
            with self.subTest(parent=parent._meta.model_name):
                url, data = self.component_request(parent, "new[1-2]")
                with patch.object(InterfaceForm, "save", save):
                    response = self.client.post(url, data)
                self.assertEqual(response.status_code, 500)
                self.assert_no_success_message(response)
                self.assertFalse(Interface.objects.filter(name__startswith="new").exists())

    def test_component_form_error_rolls_back_earlier_inserts(self):
        def clean_name(form):
            name = form.cleaned_data["name"]
            if name == "new2":
                raise ValidationError("Invalid component name.")
            return name

        for parent in (self.device, self.module):
            with self.subTest(parent=parent._meta.model_name):
                url, data = self.component_request(parent, "new[1-2]")
                with patch.object(InterfaceForm, "clean_name", clean_name, create=True):
                    response = self.client.post(url, data)
                self.assertContains(response, "Invalid component name.")
                self.assert_no_success_message(response)
                self.assertFalse(Interface.objects.filter(name__startswith="new").exists())

    def test_component_validation_conflict_is_reported(self):
        for parent in (self.device, self.module):
            with self.subTest(parent=parent._meta.model_name):
                url, data = self.component_request(parent, "existing")
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assert_no_success_message(response)

    def test_successful_component_creation(self):
        for parent in (self.device, self.module):
            with self.subTest(parent=parent._meta.model_name):
                url, data = self.component_request(parent, "created[1-2]")
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302, response.content)
                self.assertEqual(parent.interfaces.filter(name__startswith="created").count(), 2)

    def ip_create_data(self, pattern):
        return {
            "pattern": pattern,
            "namespace": str(self.ip.parent.namespace_id),
            "status": str(self.status.pk),
            "type": "host",
        }

    def test_pattern_creation_validation_error_rolls_back(self):
        # Only the first address has a parent prefix in this namespace.
        response = self.client.post(reverse("ipam:ipaddress_bulk_add"), self.ip_create_data("192.0.[2-3].2/24"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["model_form"].errors)
        self.assert_no_success_message(response)
        self.assertFalse(IPAddress.objects.filter(parent=self.ip.parent, host="192.0.2.2").exists())

    def test_pattern_creation_database_error_propagates_and_rolls_back(self):
        self.client.raise_request_exception = False
        original_save = IPAddressBulkAddForm.save

        def save(form, *args, **kwargs):
            if str(form.instance.host) == "192.0.2.3":
                form.instance.address = self.ip.address
            return original_save(form, *args, **kwargs)

        with patch.object(IPAddressBulkAddForm, "save", save):
            response = self.client.post(reverse("ipam:ipaddress_bulk_add"), self.ip_create_data("192.0.2.[2-3]/24"))
        self.assertEqual(response.status_code, 500)
        self.assert_no_success_message(response)
        self.assertFalse(IPAddress.objects.filter(parent=self.ip.parent, host="192.0.2.2").exists())
