from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from celery.utils.log import get_task_logger

from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.jobs import Job
from nautobot.extras.models import CustomField


logger = get_task_logger(__name__)


class TestCreateLocationWithCustomField(Job):
    class Meta:
        name = "Location and Custom Field Creation"
        description = "Location with a custom field"

    def run(self):
        with transaction.atomic():
            obj_type = ContentType.objects.get_for_model(Location)
            cf = CustomField(label="cf1", type=CustomFieldTypeChoices.TYPE_TEXT, default="-")
            cf.validated_save()
            cf.content_types.set([obj_type])

            logger.info("CustomField created successfully.", extra={"object": cf})

            location_type = LocationType.objects.create(name="Test Location Type 1")
            location_1 = Location.objects.create(
                name="Test Location", slug="test-location-one", location_type=location_type
            )
            location_1.cf[cf.key] = "some-value"
            location_1.save()
            logger.info("Created a new location", extra={"object": location_1})

            location_2 = Location.objects.create(
                name="Test Site Two", slug="test-location-two", location_type=location_type
            )
            logger.info("Created another new location", extra={"object": location_2})

            return "Job completed."


register_jobs(TestCreateLocationWithCustomField)
