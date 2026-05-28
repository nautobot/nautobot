"""Tests for ``nautobot.apps.dcim.SkipAutoComponentCreation``."""

import threading

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.apps.dcim import is_auto_component_creation_suppressed, SkipAutoComponentCreation
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleType,
)
from nautobot.extras.models import Role, Status


def _status_for(model):
    """Return a Status valid for ``model``, creating one if none is associated."""
    status = Status.objects.get_for_model(model).first()
    if status is None:
        status = Status.objects.create(name=f"{model.__name__} Test Status")
        status.content_types.add(ContentType.objects.get_for_model(model))
    return status


class SkipAutoComponentCreationContextManagerTestCase(TestCase):
    """Unit tests for the context manager itself (no DB writes required)."""

    def test_default_inactive(self):
        """Suppression is off by default."""
        self.assertFalse(is_auto_component_creation_suppressed())

    def test_activates_and_restores(self):
        """The flag is set inside the block and cleared on exit."""
        with SkipAutoComponentCreation():
            self.assertTrue(is_auto_component_creation_suppressed())
        self.assertFalse(is_auto_component_creation_suppressed())

    def test_nested(self):
        """An outer block keeps suppressing after an inner block exits."""
        with SkipAutoComponentCreation():
            with SkipAutoComponentCreation():
                self.assertTrue(is_auto_component_creation_suppressed())
            self.assertTrue(is_auto_component_creation_suppressed())
        self.assertFalse(is_auto_component_creation_suppressed())

    def test_exception_safe(self):
        """An exception inside the block still restores the previous state."""
        raised = False
        try:
            with SkipAutoComponentCreation():
                self.assertTrue(is_auto_component_creation_suppressed())
                raise RuntimeError("boom")
        except RuntimeError:
            raised = True
        self.assertTrue(raised)
        self.assertFalse(is_auto_component_creation_suppressed())

    def test_isolated_across_threads(self):
        """Suppression in one thread does not leak into a separately spawned thread."""
        captured = {}

        def worker():
            captured["value"] = is_auto_component_creation_suppressed()

        with SkipAutoComponentCreation():
            self.assertTrue(is_auto_component_creation_suppressed())
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

        # A freshly spawned thread starts with its own (default) context.
        self.assertFalse(captured["value"])


class SkipAutoComponentCreationOnSaveTestCase(TestCase):
    """End-to-end tests that Device/Module honour the suppression flag on initial save."""

    @classmethod
    def setUpTestData(cls):
        """Build a DeviceType and ModuleType that each define interface templates."""
        cls.manufacturer = Manufacturer.objects.create(name="Test Manufacturer #9026")

        cls.device_type = DeviceType.objects.create(manufacturer=cls.manufacturer, model="Test Model #9026")
        for name in ("eth0", "eth1"):
            InterfaceTemplate.objects.create(
                device_type=cls.device_type,
                name=name,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            )

        cls.module_type = ModuleType.objects.create(manufacturer=cls.manufacturer, model="Test Module #9026")
        InterfaceTemplate.objects.create(
            module_type=cls.module_type,
            name="mod-eth0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
        )

        cls.location_type = LocationType.objects.create(name="Test Location Type #9026")
        cls.location_type.content_types.add(ContentType.objects.get_for_model(Device))
        cls.location = Location.objects.create(
            name="Test Location #9026",
            location_type=cls.location_type,
            status=_status_for(Location),
        )

        cls.device_role = Role.objects.create(name="Test Role #9026")
        cls.device_role.content_types.add(ContentType.objects.get_for_model(Device))

        cls.device_status = _status_for(Device)
        cls.module_status = _status_for(Module)

    def _create_device(self, name):
        return Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            name=name,
            location=self.location,
        )

    def _create_module(self, device, bay_name):
        module_bay = ModuleBay.objects.create(parent_device=device, name=bay_name, position=bay_name)
        return Module.objects.create(
            module_type=self.module_type,
            parent_module_bay=module_bay,
            status=self.module_status,
        )

    # --- Default behaviour --------------------------------------------------------

    def test_device_components_created_by_default(self):
        """Without opting in, a new Device still gets its template components."""
        device = self._create_device("default-device")
        self.assertEqual(device.interfaces.count(), 2)

    def test_module_components_created_by_default(self):
        """Without opting in, a new Module still gets its template components."""
        device = self._create_device("module-parent-default")
        module = self._create_module(device, "bay-default")
        self.assertEqual(module.interfaces.count(), 1)

    # --- Suppression --------------------------------------------------------------

    def test_device_components_suppressed_in_context(self):
        """Inside the context manager, a new Device gets no auto components."""
        with SkipAutoComponentCreation():
            device = self._create_device("suppressed-device")
        self.assertEqual(device.interfaces.count(), 0)

    def test_module_components_suppressed_in_context(self):
        """Inside the context manager, a new Module gets no auto components."""
        device = self._create_device("module-parent-suppressed")
        with SkipAutoComponentCreation():
            module = self._create_module(device, "bay-suppressed")
        self.assertEqual(module.interfaces.count(), 0)

    # --- Scope -------------------------------------------------------------------

    def test_suppression_only_applies_inside_context(self):
        """A Device created after the context exits gets its default components."""
        with SkipAutoComponentCreation():
            suppressed_device = self._create_device("inside-context")
        following_device = self._create_device("outside-context")
        self.assertEqual(suppressed_device.interfaces.count(), 0)
        self.assertEqual(following_device.interfaces.count(), 2)

    def test_suppression_only_applies_on_initial_creation(self):
        """A subsequent save() of an existing Device does not re-trigger create_components()."""
        device = self._create_device("update-target")
        self.assertEqual(device.interfaces.count(), 2)
        # Mutate and save again with suppression active — components should not change either way.
        device.name = "update-target-renamed"
        with SkipAutoComponentCreation():
            device.save()
        device.refresh_from_db()
        self.assertEqual(device.interfaces.count(), 2)
