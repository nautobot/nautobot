from django.contrib.contenttypes.models import ContentType
from django.test import tag

from nautobot.core.testing.integration import (
    BulkOperationsTestCases,
)
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.models import Status


@tag("fix_in_v3")
class LocationBulkOperationsTestCase(BulkOperationsTestCases.BulkOperationsTestCase):
    """
    Test locations bulk edit / delete operations.
    """

    model_menu_path = ("Organization", "Locations")
    model_base_viewname = "dcim:location"
    model_edit_data = {"description": "Test description"}
    model_filter_by = {"location_type": "External"}
    model_class = Location
    model_expected_counts: dict[str, int] = {
        "all": 5,
        "filtered": 2,
    }
    all_count = 5

    def setup_items(self):
        self.model_expected_counts["all"] = Location.objects.count() + self.all_count
        # Create locations for test
        self.create_location("Test Location Integration Test 1")
        self.create_location("Test Location Integration Test 2")
        self.create_location("Test Location Integration Test 3")
        self.create_location("Test Location Integration Test 4", "External")
        self.create_location("Test Location Integration Test 5", "External")

    @staticmethod
    def create_location(location_name, location_type="Internal"):
        location_type, location_type_created = LocationType.objects.get_or_create(name=location_type)
        if location_type_created:
            location_type.content_types.add(ContentType.objects.get_for_model(Device))
            location_type.save()

        location_status = Status.objects.get_for_model(Location).first()
        Location.objects.get_or_create(
            name=location_name,
            status=location_status,
            location_type=location_type,
        )
