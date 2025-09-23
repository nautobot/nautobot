from django.contrib.contenttypes.models import ContentType
from django.test import tag
from django.urls import reverse

from nautobot.core.testing.integration import ObjectDetailsMixin, SeleniumTestCase
from nautobot.dcim.models import Device, PowerPanel
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation

from . import create_test_device


class RelationshipsTestCase(SeleniumTestCase, ObjectDetailsMixin):
    """
    Integration test to check nautobot.extras.models.Relationship.advanced_ui functionality
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    @tag("fix_in_v3")
    def test_relationship_advanced_ui(self):
        """
        This test creates a device and a relationship for that device.
        It first leaves the relationship advanced_ui default of False to be show on the primary information
        tab in the UI and checks it is there.
        It secondly sets the relationship to be shown only in the "Advanced" tab in the UI and checks it appears ONLY there!.
        """
        device = create_test_device()
        power_panel = PowerPanel.objects.create(
            location=device.location,
            name="Test-Power-Panel",
        )
        power_panel_ct = ContentType.objects.get_for_model(PowerPanel)
        device_content_type = ContentType.objects.get_for_model(Device)
        relationship = Relationship.objects.create(
            label="Device 2 Power Panel relationship",
            key="device_2_power_panel_relationship",
            source_type=device_content_type,
            destination_type=power_panel_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        RelationshipAssociation.objects.create(
            relationship=relationship,
            source=device,
            destination=power_panel,
        )
        # Visit the device detail page
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:device', kwargs={'pk': device.pk})}")
        # Check the relationship appears in the primary information tab
        self.assertTrue(self.browser.is_text_present("Test-Power-Panel"))  # related object
        self.assertTrue(self.browser.is_text_present("Power Panel"))  # relationship label
        # Check the relationship does NOT appear in the advanced tab
        self.switch_tab("Advanced")
        self.assertFalse(self.browser.is_text_present("Test-Power-Panel"))
        self.assertFalse(self.browser.is_text_present("Power Panel"))
        # Set the custom_field to only show in the advanced tab
        relationship.advanced_ui = True
        relationship.save()
        # Visit the device detail page
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:device', kwargs={'pk': device.pk})}")
        # Check the relationship does NOT appear in the primary information tab
        self.assertFalse(self.browser.is_text_present("Test-Power-Panel"))
        self.assertFalse(self.browser.is_text_present("Power Panel"))
        # Check the relationship appears in the advanced tab
        self.switch_tab("Advanced")
        self.assertTrue(self.browser.is_text_present("Test-Power-Panel"))
        self.assertTrue(self.browser.is_text_present("Power Panel"))
