from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.dcim.models import (
    Device,
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import JobLogEntry, Role, Status


def create_common_data_for_software_related_test_cases():
    manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
    Platform.objects.create(name="Platform 1")
    platform = Platform.objects.create(name="Platform 2", manufacturer=manufacturer)

    status = Status.objects.first()
    software_version_ct = ContentType.objects.get_for_model(SoftwareVersion)
    software_image_file_ct = ContentType.objects.get_for_model(SoftwareImageFile)
    status.content_types.add(software_version_ct)
    status.content_types.add(software_image_file_ct)

    software_version = SoftwareVersion.objects.create(
        platform=platform,
        version="Test version 1.0.0",
        status=status,
    )
    software_image_file = SoftwareImageFile.objects.create(
        software_version=software_version,
        image_file_name="software_image_file_qs_test_1.bin",
        status=status,
    )

    device_type = DeviceType.objects.create(
        manufacturer=manufacturer,
        model="Cisco CSR1000v",
        u_height=0,
    )

    device_ct = ContentType.objects.get_for_model(Device)

    device_role = Role.objects.create(name="Device Status")
    device_role.content_types.set([device_ct])

    location_type = LocationType.objects.create(name="Test Location Type")
    location_type.content_types.set([device_ct])
    location = Location.objects.create(
        name="Device Location",
        location_type=location_type,
        status=Status.objects.get_for_model(Location).first(),
    )
    device_status = Status.objects.get_for_model(Device).first()
    Device.objects.create(
        device_type=device_type,
        role=device_role,
        name="Device 1",
        location=location,
        status=device_status,
        software_version=software_version,
    )
    DeviceTypeToSoftwareImageFile.objects.create(device_type=device_type, software_image_file=software_image_file)


class TestSoftwareImageFileTestCase(TransactionTestCase):
    def test_correct_handling_for_model_protected_error(self):
        create_common_data_for_software_related_test_cases()
        software_image_file = SoftwareImageFile.objects.get(image_file_name="software_image_file_qs_test_1.bin")

        self.add_permissions("dcim.delete_softwareimagefile")
        pk_list = [str(software_image_file.pk)]
        initial_count = SoftwareImageFile.objects.all().count()

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=ContentType.objects.get_for_model(SoftwareImageFile).id,
            delete_all=False,
            filter_query_params={},
            pk_list=pk_list,
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertIn("Caught ProtectedError while attempting to delete objects", error_log.message)
        self.assertEqual(initial_count, SoftwareImageFile.objects.all().count())


class TestSoftwareVersionTestCase(TransactionTestCase):
    def test_correct_handling_for_model_protected_error(self):
        create_common_data_for_software_related_test_cases()
        software_version = SoftwareVersion.objects.get(version="Test version 1.0.0")

        initial_count = SoftwareVersion.objects.all().count()
        self.add_permissions("dcim.delete_softwareversion")
        pk_list = [str(software_version.pk)]

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=ContentType.objects.get_for_model(SoftwareVersion).id,
            delete_all=False,
            filter_query_params={},
            pk_list=pk_list,
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertIn("Caught ProtectedError while attempting to delete objects", error_log.message)
        self.assertEqual(initial_count, SoftwareVersion.objects.all().count())
