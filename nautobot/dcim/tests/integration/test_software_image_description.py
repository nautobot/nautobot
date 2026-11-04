from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import InventoryItem, Platform, SoftwareImageFile, SoftwareVersion
from nautobot.extras.models import Status
from nautobot.extras.tests.integration import create_test_device
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine

DEVICE_TYPE_MARKER = '<b class="ncsat-marker">device type</b>'
SOFTWARE_VERSION_MARKER = '<b class="ncsat-marker">software version</b>'


class SoftwareImageDescriptionTestCase(SeleniumTestCase):
    """The software image summary on edit forms must show device type and software version names as plain text."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        platform = Platform.objects.create(name="Software Image Description Platform")
        software_version = SoftwareVersion(
            platform=platform,
            version="1.0.0",
            alias=SOFTWARE_VERSION_MARKER,
            status=Status.objects.get_for_model(SoftwareVersion).first(),
        )
        software_version.validated_save()
        # A default image with no device type mappings shows both names in the Device form's summary.
        SoftwareImageFile(
            software_version=software_version,
            image_file_name="software-image.bin",
            default_image=True,
            status=Status.objects.get_for_model(SoftwareImageFile).first(),
        ).validated_save()

        self.device = create_test_device("Software Image Description Device")
        self.device.device_type.model = DEVICE_TYPE_MARKER
        self.device.device_type.validated_save()
        self.device.software_version = software_version
        self.device.validated_save()

        self.inventory_item = InventoryItem(
            device=self.device,
            name="Software Image Description Inventory Item",
            software_version=software_version,
        )
        self.inventory_item.validated_save()

        cluster_type = ClusterType.objects.create(name="Software Image Description Cluster Type")
        cluster = Cluster.objects.create(name="Software Image Description Cluster", cluster_type=cluster_type)
        self.virtual_machine = VirtualMachine(
            name="Software Image Description VM",
            cluster=cluster,
            status=Status.objects.get_for_model(VirtualMachine).first(),
            software_version=software_version,
        )
        self.virtual_machine.validated_save()

    def tearDown(self):
        self.logout()
        super().tearDown()

    def assert_description_shows_text(self, *markers):
        self.assertTrue(self.browser.is_element_present_by_css("#software_version_image_list a", wait_time=10))
        description = self.browser.find_by_css("#software_version_image_description").first
        for marker in markers:
            self.assertIn(marker, description.text)
        self.assertTrue(self.browser.is_element_not_present_by_css("#software_version_image_description .ncsat-marker"))

    def test_device_edit_form_renders_names_as_text(self):
        self.browser.visit(self.live_server_url + reverse("dcim:device_edit", kwargs={"pk": self.device.pk}))
        self.assert_description_shows_text(SOFTWARE_VERSION_MARKER, DEVICE_TYPE_MARKER)

    def test_inventory_item_edit_form_renders_names_as_text(self):
        self.browser.visit(
            self.live_server_url + reverse("dcim:inventoryitem_edit", kwargs={"pk": self.inventory_item.pk})
        )
        self.assert_description_shows_text(SOFTWARE_VERSION_MARKER)

    def test_virtual_machine_edit_form_renders_names_as_text(self):
        self.browser.visit(
            self.live_server_url + reverse("virtualization:virtualmachine_edit", kwargs={"pk": self.virtual_machine.pk})
        )
        self.assert_description_shows_text(SOFTWARE_VERSION_MARKER)
