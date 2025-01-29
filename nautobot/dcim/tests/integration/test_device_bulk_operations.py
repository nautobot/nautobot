import uuid

from nautobot.core.testing.integration import (
    BulkOperationsTestCases,
)
from nautobot.dcim.models import Device
from nautobot.extras.tests.integration import create_test_device


class DeviceBulkOperationsTestCase(BulkOperationsTestCases.BulkOperationsTestCase):
    """
    Test devices bulk edit / delete operations.
    """

    model_menu_path = ("Devices", "Devices")
    model_base_viewname = "dcim:device"
    model_edit_data = {"serial": "Test serial"}
    model_filter_by = {"location": "Test Location 2"}
    model_class = Device

    def setup_items(self):
        Device.objects.all().delete()
        test_uuid = str(uuid.uuid4())

        # Create device for test
        create_test_device("Test Device Integration Test 1", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 2", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 3", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 4", "Test Location 2", test_uuid=test_uuid)
        create_test_device("Test Device Integration Test 5", "Test Location 2", test_uuid=test_uuid)
