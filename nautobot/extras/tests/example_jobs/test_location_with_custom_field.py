from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.jobs import Job
from nautobot.extras.models import CustomField


class TestCreateLocationWithCustomField(Job):
    class Meta:
        name = "Location and Custom Field Creation"
        description = "Location with a custom field"

    def run(self, data, commit):
        obj_type = ContentType.objects.get_for_model(Location)
        cf = CustomField(name="cf1", type=CustomFieldTypeChoices.TYPE_TEXT, default="-")
        cf.validated_save()
        cf.content_types.set([obj_type])

        self.log_success(obj=cf, message="CustomField created successfully.")

        location_type = LocationType.objects.get(name="Campus")
        location_1 = Location.objects.create(
            name="Test Site One", slug="test-location-one", location_type=location_type
        )
        # 2.0 TODO: #824 cf.slug rather than cf.name
        location_1.cf[cf.name] = "some-value"
        location_1.save()
        self.log_success(obj=location_1, message="Created a new location")

        location_2 = Location.objects.create(
            name="Test Site Two", slug="test-location-two", location_type=location_type
        )
        self.log_success(obj=location_2, message="Created another new location")

        return "Job completed."
