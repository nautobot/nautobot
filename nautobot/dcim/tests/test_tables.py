from django.test import TestCase

from nautobot.dcim.choices import InterfaceDuplexChoices, InterfaceSpeedChoices, InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, InterfaceTemplate, Location, LocationType, Manufacturer
from nautobot.dcim.tables.devices import DeviceModuleInterfaceTable, InterfaceTable
from nautobot.dcim.tables.devicetypes import InterfaceTemplateTable
from nautobot.extras.models import Role, Status


class InterfaceTableRenderMixin:
    """Mixin for testing render_speed methods on interface tables."""

    table_class = None

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Test Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.filter(location_type=location_type).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.interface_status = Status.objects.get_for_model(Interface).first()

        cls.device = Device.objects.create(
            name="Test Device",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )

    def test_render_speed_duplex_with_value(self):
        """Test that the table renders humanized speed values."""
        interface = Interface.objects.create(
            device=self.device,
            name="eth0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=self.interface_status,
            speed=InterfaceSpeedChoices.SPEED_1G,
            duplex=InterfaceDuplexChoices.DUPLEX_FULL,
        )

        queryset = Interface.objects.filter(pk=interface.pk)
        table = self.table_class(queryset)  # pylint: disable=not-callable
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")
        rendered_duplex = bound_row.get_cell("duplex")

        self.assertEqual(rendered_speed, "1 Gbps")
        self.assertEqual(rendered_duplex, "Full")

    def test_render_speed_duplex_with_none(self):
        """Test that the table handles None speed value and renders an emdash."""
        emdash = "\u2014"
        interface = Interface.objects.create(
            device=self.device,
            name="eth1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=self.interface_status,
            speed=None,
        )

        queryset = Interface.objects.filter(pk=interface.pk)
        table = self.table_class(queryset)  # pylint: disable=not-callable
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")
        rendered_duplex = bound_row.get_cell("duplex")

        self.assertEqual(rendered_speed, emdash)
        self.assertEqual(rendered_duplex, emdash)

    def test_render_speed_various(self):
        """Test that the table correctly humanizes various speed values."""
        # Test all speed choices defined in InterfaceSpeedChoices
        for speed_value, expected_output in InterfaceSpeedChoices.CHOICES:
            with self.subTest(speed_value=speed_value, expected=expected_output):
                interface = Interface.objects.create(
                    device=self.device,
                    name=f"eth-{speed_value}",
                    type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                    status=self.interface_status,
                    speed=speed_value,
                )

                queryset = Interface.objects.filter(pk=interface.pk)
                table = self.table_class(queryset)  # pylint: disable=not-callable
                bound_row = table.rows[0]
                rendered_speed = bound_row.get_cell("speed")

                self.assertEqual(rendered_speed, expected_output)

    def test_render_duplex_various(self):
        """Test that the table correctly renders various duplex values."""
        for duplex_value, expected_output in InterfaceDuplexChoices.CHOICES:
            with self.subTest(duplex_value=duplex_value, expected=expected_output):
                interface = Interface.objects.create(
                    device=self.device,
                    name=f"eth-{duplex_value}",
                    type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                    status=self.interface_status,
                    duplex=duplex_value,
                )

                queryset = Interface.objects.filter(pk=interface.pk)
                table = self.table_class(queryset)  # pylint: disable=not-callable
                bound_row = table.rows[0]
                rendered_duplex = bound_row.get_cell("duplex")

                self.assertEqual(rendered_duplex, expected_output)


class InterfaceTableTestCase(InterfaceTableRenderMixin, TestCase):
    """Test cases for InterfaceTable."""

    table_class = InterfaceTable


class DeviceModuleInterfaceTableTestCase(InterfaceTableRenderMixin, TestCase):
    """Test cases for DeviceModuleInterfaceTable."""

    table_class = DeviceModuleInterfaceTable


class InterfaceTemplateTableTestCase(TestCase):
    """Render tests for InterfaceTemplateTable speed/duplex columns."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manuf Tmpl")
        cls.device_type = DeviceType.objects.create(manufacturer=manufacturer, model="DT-Tmpl")

    def test_render_speed_duplex_with_value(self):
        interface_template = InterfaceTemplate.objects.create(
            device_type=self.device_type,
            name="tmpl-eth0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            speed=InterfaceSpeedChoices.SPEED_1G,
            duplex=InterfaceDuplexChoices.DUPLEX_FULL,
        )
        table = InterfaceTemplateTable(InterfaceTemplate.objects.filter(pk=interface_template.pk))
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")  # pylint: disable=no-member
        rendered_duplex = bound_row.get_cell("duplex")  # pylint: disable=no-member
        self.assertEqual(rendered_speed, "1 Gbps")
        self.assertEqual(rendered_duplex, "Full")

    def test_render_speed_duplex_with_none(self):
        emdash = "\u2014"
        interface_template = InterfaceTemplate.objects.create(
            device_type=self.device_type,
            name="tmpl-eth1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        table = InterfaceTemplateTable(InterfaceTemplate.objects.filter(pk=interface_template.pk))
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")  # pylint: disable=no-member
        rendered_duplex = bound_row.get_cell("duplex")  # pylint: disable=no-member
        self.assertEqual(rendered_speed, emdash)
        self.assertEqual(rendered_duplex, emdash)
