import codecs
import csv
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.utils import timezone
import yaml

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.jobs import ExportObjectList
from nautobot.core.jobs.cleanup import CleanupTypes
from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.factory import JobResultFactory, ObjectChangeFactory
from nautobot.extras.models import (
    Contact,
    ContactAssociation,
    ExportTemplate,
    FileProxy,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Role,
    SavedView,
    Status,
    Tag,
)
from nautobot.extras.models.metadata import ObjectMetadata
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.users.models import ObjectPermission


class ExportObjectListTest(TransactionTestCase):
    """
    Test the ExportObjectList system job.
    """

    databases = ("default", "job_logs")

    def _create_saved_view(self, model_class=Status, config=None):
        """Helper to create a SavedView with optional filter config."""
        return SavedView.objects.create(
            name="Global default View",
            owner=self.user,
            view=f"{model_class._meta.app_label}:{model_class._meta.model_name}_list",
            is_global_default=True,
            config=config or {},
        )

    def _run_export_job(self, query_string, model_class=Status):
        """Helper to run export job and return parsed CSV rows."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(model_class).pk,
            query_string=query_string,
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(
            Path(job_result.files.first().file.name).name, f"nautobot_{model_class._meta.verbose_name_plural}.csv"
        )
        csv_data = job_result.files.first().file.read().decode("utf-8").lstrip("\ufeff")
        return list(csv.DictReader(StringIO(csv_data)))

    def test_export_without_permission(self):
        """Job should enforce user permissions on the content-type being asked for export."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(log_error.message, f'User "{self.user}" does not have permission to view status objects')
        self.assertFalse(job_result.files.exists())

    def test_export_with_constrained_permission(self):
        """Job should only allow the user to export objects they have permission to view."""
        instance1, instance2 = Status.objects.all()[:2]
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_statuses.csv")
        csv_bytes = job_result.files.first().file.read()
        self.assertTrue(csv_bytes.startswith(codecs.BOM_UTF8), csv_bytes)
        csv_data = csv_bytes.decode("utf-8")
        self.assertIn(str(instance1.pk), csv_data)
        self.assertNotIn(str(instance2.pk), csv_data)

    def test_export_all_to_csv(self):
        """By default, job should export all instances to CSV."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_statuses.csv")
        csv_data = job_result.files.first().file.read().decode("utf-8")
        # May be more than one line per Status if they have newlines in their description strings
        self.assertGreaterEqual(len(csv_data.split("\n")), Status.objects.count() + 1, csv_data)  # +1 for CSV header

    def test_export_all_via_export_template(self):
        """When an export-template is specified, it should be used."""
        et = ExportTemplate.objects.create(
            content_type=ContentType.objects.get_for_model(Status),
            name="Simple Export Template",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
            file_extension="txt",
        )
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(Status).pk,
            export_template=et.pk,
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_statuses.txt")
        text_data = job_result.files.first().file.read().decode("utf-8")
        self.assertEqual(len(text_data.split("\n")), Status.objects.count() + 1)
        for status in Status.objects.iterator():
            self.assertIn(status.name, text_data)

    def test_export_devicetype_to_yaml(self):
        """Export device-type to YAML."""
        mfr = Manufacturer.objects.create(name="Cisco")
        DeviceType.objects.create(
            manufacturer=mfr,
            model="Cisco CSR1000v",
            u_height=0,
        )
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(DeviceType).pk,
            export_format="yaml",
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_device_types.yaml")
        yaml_data = job_result.files.first().file.read().decode("utf-8")
        data = yaml.safe_load(yaml_data)
        self.assertEqual(data["manufacturer"], "Cisco")

    def test_get_saved_view_filter_params(self):
        """Test various cases for the saved view filter parameters."""
        saved_view = self._create_saved_view(config={"filter_params": {"name": ["Active"]}})
        test_cases = [
            # (query_params, expected_output)
            ({"saved_view": saved_view.pk}, {"name": ["Active"]}),
            (
                {
                    "saved_view": saved_view.pk,
                    "name": ["Active"],
                    "content_types": ["dcim.devices"],
                },  # new filter content_types
                {"name": ["Active"]},
            ),
            (
                {"saved_view": saved_view.pk, "content_types": ["dcim.devices"]},  # name filter was deleted
                {},
            ),
            ({"saved_view": saved_view.pk, "all_filters_removed": "true"}, {}),
            (
                {"name": ["Active"]},  # No saved view provided
                {},
            ),
        ]

        for query_params, expected_output in test_cases:
            with self.subTest(query_params=query_params, expected_output=expected_output):
                job = ExportObjectList()
                filter_params = job._get_saved_view_filter_params(query_params)
                self.assertEqual(filter_params, expected_output)

    def test_export_saved_view_to_csv_without_filters(self):
        """Export a SavedView to CSV without any filters applied."""
        # URL: /?saved_view=<id>
        sv = self._create_saved_view()
        rows = self._run_export_job(query_string=f"saved_view={sv.pk}")
        self.assertEqual(len(rows), Status.objects.count())

    def test_export_saved_view_to_csv_with_filters_from_saved_view(self):
        """Export a SavedView to CSV using filters defined in the SavedView config."""
        # URL: /?saved_view=<id>
        filter_name = Status.objects.first().name
        sv = self._create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self._run_export_job(query_string=f"saved_view={sv.pk}")
        self.assertGreaterEqual(Status.objects.count(), 1)  # Ensure multiple Statuses exist and filter works
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], filter_name)

    def test_export_saved_view_to_csv_with_combined_filters(self):
        """Export a SavedView to CSV using combined filters from SavedView config and query params."""
        # URL: /?saved_view=<id>&name=<filter_name>&name=<filter_name2>
        filter_name = Status.objects.first().name
        filter_name2 = Status.objects.last().name
        sv = self._create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self._run_export_job(query_string=f"saved_view={sv.pk}&name={filter_name}&name={filter_name2}")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], filter_name)
        self.assertEqual(rows[1]["name"], filter_name2)

    def test_export_saved_view_manufacturer_to_csv_with_replaced_filters(self):
        """Export a SavedView manufacturer to CSV after replacing filters."""
        # URL: /?saved_view=<id>&description=<manufacturer2>
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        manufacturer2 = Manufacturer.objects.create(name="Test2 Manufacturer", description="test filter")
        filter_name = manufacturer.name
        filter_description = manufacturer2.description
        sv = self._create_saved_view(model_class=Manufacturer, config={"filter_params": {"name": [filter_name]}})
        rows = self._run_export_job(
            query_string=f"saved_view={sv.pk}&description={filter_description}", model_class=Manufacturer
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], manufacturer2.name)
        self.assertEqual(rows[0]["description"], filter_description)
        self.assertTrue(all(row["name"] != filter_name for row in rows))

    def test_export_saved_view_to_csv_after_removing_all_filters(self):
        """Export a SavedView to CSV after removing all filters."""
        # URL: /?saved_view=<id>&all_filters_removed=true
        filter_name = Status.objects.first().name
        sv = self._create_saved_view(config={"filter_params": {"name": [filter_name]}})
        rows = self._run_export_job(query_string=f"saved_view={sv.pk}&all_filters_removed=true")
        self.assertEqual(len(rows), Status.objects.count())


class ImportObjectsTestCase(TransactionTestCase):
    databases = ("default", "job_logs")

    csv_data = "\n".join(
        [
            "name,color,content_types",
            "test_status1,111111,dcim.device",
            'test_status2,222222,"dcim.device,dcim.location"',
            "test_status3,333333,dcim.device",
            "test_status4,444444,dcim.device",
        ]
    )

    def test_csv_import_without_permission(self):
        """Job should enforce user permissions on the content-type being imported."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
            csv_data=self.csv_data,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(log_error.message, f'User "{self.user}" does not have permission to create status objects')
        self.assertFalse(Status.objects.filter(name__startswith="test_status").exists())

    def test_import_without_data(self):
        """Either csv_data or csv_file arguments must be provided."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)

    def test_csv_import_with_constrained_permission(self):
        """Job should only allow the user to import objects they have permission to add."""
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"color__in": ["111111", "222222"]},
            actions=["add"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
            csv_data=self.csv_data,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_successes = JobLogEntry.objects.filter(
            job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
        )
        self.assertEqual(log_successes[0].message, 'Row 1: Created record "test_status1"')
        self.assertTrue(Status.objects.filter(name="test_status1").exists())
        self.assertEqual(log_successes[1].message, 'Row 2: Created record "test_status2"')
        self.assertTrue(Status.objects.filter(name="test_status2").exists())
        log_errors = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(
            log_errors[0].message,
            f'Row 3: User "{self.user}" does not have permission to create an object with these attributes',
        )
        self.assertFalse(Status.objects.filter(name="test_status3").exists())
        self.assertEqual(
            log_errors[1].message,
            f'Row 4: User "{self.user}" does not have permission to create an object with these attributes',
        )
        self.assertFalse(Status.objects.filter(name="test_status4").exists())
        self.assertEqual(log_successes[2].message, "Created 2 status object(s) from 4 row(s) of data")

    def test_csv_import_with_permission(self):
        """A superuser running the job with valid data should successfully create all specified objects."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Status).pk,
            csv_data=self.csv_data,
        )
        self.assertJobResultStatus(job_result)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )
        self.assertEqual(4, Status.objects.filter(name__startswith="test_status").count())

    def test_csv_import_with_utf_8_with_bom_encoding(self):
        """
        A superuser running the job with a .csv file with utf_8 with bom encoding should successfully create all specified objects.
        Test for bug fix https://github.com/nautobot/nautobot/issues/5812 and https://github.com/nautobot/nautobot/issues/5985
        """

        status = Status.objects.get(name="Active").pk
        content = f"prefix,status\n192.168.1.1/32,{status}"
        content = content.encode("utf-8-sig")
        filename = "test.csv"
        csv_file = FileProxy.objects.create(name=filename, file=ContentFile(content, name=filename))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Prefix).pk,
            csv_file=csv_file.id,
        )
        self.assertJobResultStatus(job_result)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )
        self.assertEqual(
            1, Prefix.objects.filter(status=Status.objects.get(name="Active"), prefix="192.168.1.1/32").count()
        )
        mfr = Manufacturer.objects.create(name="Test Cisco Manufacturer")
        device_type = DeviceType.objects.create(
            manufacturer=mfr,
            model="Cisco CSR1000v",
            u_height=0,
        )
        location_type = LocationType.objects.create(name="Test Location Type")
        location_type.content_types.set([ContentType.objects.get_for_model(Device)])
        location = Location.objects.create(
            name="Device Location",
            location_type=location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        role = Role.objects.create(name="Device Status")
        role.content_types.set([ContentType.objects.get_for_model(Device)])
        content = "\n".join(
            [
                "serial,asset_tag,device_type,location,status,name,role",
                f"1021C4,CA211,{device_type.pk},{location.pk},{status},Test-AC-01,{role}",
                f"1021C5,CA212,{device_type.pk},{location.pk},{status},Test-AC-02,{role}",
            ]
        )
        content = content.encode("utf-8-sig")
        filename = "test.csv"
        csv_file = FileProxy.objects.create(name=filename, file=ContentFile(content, name=filename))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Device).pk,
            csv_file=csv_file.id,
        )
        self.assertJobResultStatus(job_result)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )
        device_1 = Device.objects.get(name="Test-AC-01")
        device_2 = Device.objects.get(name="Test-AC-02")
        self.assertEqual(device_1.serial, "1021C4")
        self.assertEqual(device_2.serial, "1021C5")

    def test_csv_import_bad_row(self):
        """A row of incorrect data should fail validation for that object but import all others successfully if `roll_back_if_error` is False."""
        csv_data = self.csv_data.split("\n")
        csv_data.insert(1, "test_status0,notacolor,dcim.device")
        csv_data = "\n".join(csv_data)

        with self.subTest("Assert `roll_back_if_error`: if error all records are rolled back"):
            job_result = create_job_result_and_run_job(
                "nautobot.core.jobs",
                "ImportObjects",
                content_type=ContentType.objects.get_for_model(Status).pk,
                csv_data=csv_data,
                roll_back_if_error=True,
            )
            self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
            log_info = JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
            )
            for idx, status_name in enumerate(("test_status1", "test_status2", "test_status3", "test_status4")):
                self.assertIn(f'Created record "{status_name}"', log_info[idx].message)
                self.assertFalse(Status.objects.filter(name=status_name).exists())

            log_errors = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
            self.assertEqual(log_errors[0].message, "Row 1: `color`: `Enter a valid hexadecimal RGB color code.`")

            log_warning = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING)
            self.assertEqual(log_warning[0].message, "Rolling back all 4 records.")
            self.assertEqual(log_warning[1].message, "No status objects were created")

        with self.subTest("Assert all other data are imported successfully if `roll_back_if_error` is False"):
            job_result = create_job_result_and_run_job(
                "nautobot.core.jobs",
                "ImportObjects",
                content_type=ContentType.objects.get_for_model(Status).pk,
                csv_data=csv_data,
            )
            self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
            log_errors = JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
            self.assertEqual(log_errors[0].message, "Row 1: `color`: `Enter a valid hexadecimal RGB color code.`")
            self.assertFalse(Status.objects.filter(name="test_status0").exists())
            log_successes = JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_INFO, message__icontains="created"
            )
            self.assertEqual(log_successes[0].message, 'Row 2: Created record "test_status1"')
            self.assertTrue(Status.objects.filter(name="test_status1").exists())
            self.assertEqual(log_successes[1].message, 'Row 3: Created record "test_status2"')
            self.assertTrue(Status.objects.filter(name="test_status2").exists())
            self.assertEqual(log_successes[2].message, 'Row 4: Created record "test_status3"')
            self.assertTrue(Status.objects.filter(name="test_status3").exists())
            self.assertEqual(log_successes[3].message, 'Row 5: Created record "test_status4"')
            self.assertTrue(Status.objects.filter(name="test_status4").exists())
            self.assertEqual(log_successes[4].message, "Created 4 status object(s) from 5 row(s) of data")

    def test_csv_import_contact_assignment(self):
        self.add_permissions(
            "dcim.view_locationtype",
            "extras.view_status",
            "dcim.view_location",
            "extras.add_role",
            "extras.add_contact",
        )
        location_types_csv = "\n".join(["name", "ContactAssignmentImportTestLocationType"])
        locations_csv = "\n".join(
            [
                "location_type__name,name,status__name",
                "ContactAssignmentImportTestLocationType,ContactAssignmentImportTestLocation1,Active",
                "ContactAssignmentImportTestLocationType,ContactAssignmentImportTestLocation2,Active",
            ]
        )
        roles_csv = "\n".join(
            [
                "name,content_types",
                "ContactAssignmentImportTestLocation-On Site,extras.contactassociation",
            ]
        )
        contacts_csv = "\n".join(["name,email", "Bob-ContactAssignmentImportTestLocation,bob@example.com"])

        location_types_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(LocationType).pk,
            csv_data=location_types_csv,
        )
        self.assertJobResultStatus(location_types_job_result)

        location_type_count = LocationType.objects.filter(name="ContactAssignmentImportTestLocationType").count()
        self.assertEqual(location_type_count, 1, f"Unexpected count of LocationTypes {location_type_count}")

        locations_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Location).pk,
            csv_data=locations_csv,
        )
        self.assertJobResultStatus(locations_job_result)

        location_count = Location.objects.filter(location_type__name="ContactAssignmentImportTestLocationType").count()
        self.assertEqual(location_count, 2, f"Unexpected count of Locations {location_count}")

        contacts_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Contact).pk,
            csv_data=contacts_csv,
        )
        self.assertJobResultStatus(contacts_job_result)

        contact_count = Contact.objects.filter(name="Bob-ContactAssignmentImportTestLocation").count()
        self.assertEqual(contact_count, 1, f"Unexpected number of contacts {contact_count}")

        roles_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(Role).pk,
            csv_data=roles_csv,
        )
        self.assertJobResultStatus(roles_job_result)

        role_count = Role.objects.filter(name="ContactAssignmentImportTestLocation-On Site").count()
        self.assertEqual(role_count, 1, f"Unexpected number of role values {role_count}")

        associations = ["associated_object_id,associated_object_type,status__name,role__name,contact__name"]
        for location in Location.objects.filter(location_type__name="ContactAssignmentImportTestLocationType"):
            associations.append(
                f"{location.pk},dcim.location,Active,ContactAssignmentImportTestLocation-On Site,Bob-ContactAssignmentImportTestLocation"
            )
        associations_csv = "\n".join(associations)

        associations_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ImportObjects",
            content_type=ContentType.objects.get_for_model(ContactAssociation).pk,
            csv_data=associations_csv,
        )
        self.assertJobResultStatus(associations_job_result)


class LogsCleanupTestCase(TransactionTestCase):
    """
    Test the LogsCleanup system job.
    """

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()
        # Recall that TransactionTestCase truncates the DB after each test case...
        cache.delete("nautobot.extras.utils.change_logged_models_queryset")
        if ObjectChange.objects.count() < 2:
            ObjectChangeFactory.create_batch(40)
        if JobResult.objects.count() < 2:
            JobResultFactory.create_batch(20)

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["*"],
                },
            }
        }
    )
    def test_cleanup_without_permission(self):
        """Job should enforce user permissions on the content-types being deleted."""
        job_result_count = JobResult.objects.count()
        job_log_entry_count = JobLogEntry.objects.count()
        object_change_count = ObjectChange.objects.count()

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            username=self.user.username,
            cleanup_types=[CleanupTypes.JOB_RESULT],
            max_age=0,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(log_error.message, f'User "{self.user}" does not have permission to delete JobResult records')
        self.assertEqual(JobResult.objects.count(), job_result_count + 1)
        self.assertGreater(JobLogEntry.objects.count(), job_log_entry_count)
        self.assertEqual(ObjectChange.objects.count(), object_change_count)

        with self.assertLogs("nautobot.events") as cm:
            job_result = create_job_result_and_run_job(
                "nautobot.core.jobs.cleanup",
                "LogsCleanup",
                username=self.user.username,
                cleanup_types=[CleanupTypes.OBJECT_CHANGE],
                max_age=0,
            )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(
            log_error.message, f'User "{self.user}" does not have permission to delete ObjectChange records'
        )
        self.assertEqual(JobResult.objects.count(), job_result_count + 2)
        self.assertGreater(JobLogEntry.objects.count(), job_log_entry_count)
        self.assertEqual(ObjectChange.objects.count(), object_change_count)

        complete_logs = {
            "job_result_id": str(job_result.id),
            "job_name": "Logs Cleanup",
            "user_name": self.user.username,
            "job_kwargs": {"cleanup_types": ["extras.ObjectChange"], "max_age": 0},
            "einfo": {
                "exc_type": "PermissionDenied",
                "exc_message": "User does not have delete permissions for ObjectChange records",
            },
        }
        self.assertEqual(
            cm.output[1],
            f"INFO:nautobot.events.nautobot.jobs.job.completed:{json.dumps(complete_logs, indent=4)}",
        )

    def test_cleanup_with_constrained_permission(self):
        """Job should only allow the user to cleanup records they have permission to delete."""
        job_result_1 = JobResult.objects.last()
        job_result_2 = JobResult.objects.first()
        self.assertNotEqual(job_result_1.pk, job_result_2.pk)
        object_change_1 = ObjectChange.objects.first()
        object_change_2 = ObjectChange.objects.last()
        self.assertNotEqual(object_change_1.pk, object_change_2.pk)
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk__in": [str(job_result_1.pk), str(object_change_1.pk)]},
            actions=["delete"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(JobResult))
        obj_perm.object_types.add(ContentType.objects.get_for_model(ObjectChange))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            username=self.user.username,
            cleanup_types=[CleanupTypes.JOB_RESULT, CleanupTypes.OBJECT_CHANGE],
            max_age=0,
        )
        self.assertJobResultStatus(job_result)
        self.assertEqual(job_result.result["extras.JobResult"], 1)
        self.assertEqual(job_result.result["extras.ObjectChange"], 1)
        with self.assertRaises(JobResult.DoesNotExist):
            JobResult.objects.get(pk=job_result_1.pk)
        JobResult.objects.get(pk=job_result_2.pk)
        with self.assertRaises(ObjectChange.DoesNotExist):
            ObjectChange.objects.get(pk=object_change_1.pk)
        ObjectChange.objects.get(pk=object_change_2.pk)

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["*"],
                },
            }
        }
    )
    def test_cleanup_job_results(self):
        """With unconstrained permissions, all JobResults before the cutoff should be deleted."""
        cutoff = timezone.now() - timedelta(days=60)
        job_results_to_be_deleted = JobResult.objects.filter(date_done__lt=cutoff)
        job_results_to_be_deleted_count = job_results_to_be_deleted.count()
        job_log_entry_to_be_deleted_count = JobLogEntry.objects.filter(job_result__in=job_results_to_be_deleted).count()
        objectmetadata_to_be_deleted_count = ObjectMetadata.objects.filter(
            assigned_object_id__in=job_results_to_be_deleted,
            assigned_object_type=ContentType.objects.get_for_model(JobResult),
        ).count()

        with self.assertLogs("nautobot.events") as cm:
            job_result = create_job_result_and_run_job(
                "nautobot.core.jobs.cleanup",
                "LogsCleanup",
                cleanup_types=[CleanupTypes.JOB_RESULT],
                max_age=60,
            )
        self.assertFalse(JobResult.objects.filter(date_done__lt=cutoff).exists(), cm.output)
        self.assertTrue(JobResult.objects.filter(date_done__gte=cutoff).exists(), cm.output)
        self.assertTrue(ObjectChange.objects.filter(time__lt=cutoff).exists(), cm.output)
        self.assertTrue(ObjectChange.objects.filter(time__gte=cutoff).exists(), cm.output)

        started_logs = {
            "job_result_id": str(job_result.id),
            "job_name": "Logs Cleanup",
            "user_name": job_result.user.username,
            "job_kwargs": {"cleanup_types": ["extras.JobResult"], "max_age": 60},
        }
        self.assertEqual(
            cm.output[0],
            f"INFO:nautobot.events.nautobot.jobs.job.started:{json.dumps(started_logs, indent=4)}",
        )

        started_logs["job_output"] = {
            "extras.JobResult": job_results_to_be_deleted_count,
            "extras.JobLogEntry": job_log_entry_to_be_deleted_count,
        }
        if objectmetadata_to_be_deleted_count > 0:
            started_logs["job_output"]["extras.ObjectMetadata"] = objectmetadata_to_be_deleted_count

        self.assertEqual(
            cm.output[1],
            f"INFO:nautobot.events.nautobot.jobs.job.completed:{json.dumps(started_logs, indent=4)}",
        )

    def test_cleanup_object_changes(self):
        """With unconstrained permissions, all ObjectChanges before the cutoff should be deleted."""
        cutoff = timezone.now() - timedelta(days=60)
        create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            cleanup_types=[CleanupTypes.OBJECT_CHANGE],
            max_age=60,
        )
        self.assertTrue(JobResult.objects.filter(date_done__lt=cutoff).exists())
        self.assertTrue(JobResult.objects.filter(date_done__gte=cutoff).exists())
        self.assertFalse(ObjectChange.objects.filter(time__lt=cutoff).exists())
        self.assertTrue(ObjectChange.objects.filter(time__gte=cutoff).exists())


class BulkEditTestCase(TransactionTestCase):
    """
    Test the BulkEdit system job.
    """

    def setUp(self):
        super().setUp()
        self.status_ct = ContentType.objects.get_for_model(Status)
        self.namespace_ct = ContentType.objects.get_for_model(Namespace)
        self.role_ct = ContentType.objects.get_for_model(Role)
        self.ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        self.tags = [Tag.objects.create(name=f"Example Tag {x}") for x in range(5)]
        for tag in self.tags:
            tag.content_types.add(self.namespace_ct)

    def _common_no_error_test_assertion(self, model, job_result, expected_count, **filter_params):
        self.assertJobResultStatus(job_result)
        self.assertEqual(model.objects.filter(**filter_params).count(), expected_count)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )

    def test_bulk_edit_objects_without_permission(self):
        statuses = [Status.objects.create(name=f"Sample Status {x}") for x in range(3)]
        pk_list = [str(status.id) for status in statuses]
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.status_ct.id,
            edit_all=False,
            filter_query_params={},
            form_data={"pk": pk_list, "color": "aa1409"},
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        job_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(job_log.message, f'User "{self.user}" does not have permission to update status objects')

        # Assert status did not get updated
        for status in statuses:
            status.refresh_from_db()
            self.assertNotEqual(status.color, "aa1409")

    def test_bulk_edit_objects_with_constrained_permission(self):
        roles_to_update = [
            Role.objects.create(name="Example Role 1"),
            Role.objects.create(name="Example Role 2"),
        ]
        pk_list = [str(role.pk) for role in roles_to_update]

        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"pk": pk_list[0]},
            actions=["change", "view"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(self.role_ct)

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.role_ct.id,
            edit_all=False,
            filter_query_params={"per_page": 2},
            form_data={"pk": pk_list, "color": "aa1409"},
            username=self.user.username,
        )
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertIn("Form validation unsuccessful", error_log.message)
        self.assertIn(f"{roles_to_update[1].pk} is not one of the available choices.", error_log.message)
        roles_to_update[0].refresh_from_db()
        roles_to_update[1].refresh_from_db()
        self.assertNotEqual(roles_to_update[0].color, "aa1409")
        self.assertNotEqual(roles_to_update[1].color, "aa1409")

        obj_perm.constraints = {"pk__in": pk_list}
        obj_perm.save()

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.role_ct.id,
            edit_all=False,
            filter_query_params={"sort": "name"},
            form_data={"pk": pk_list, "color": "aa1409"},
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, 2, pk__in=pk_list, color="aa1409")

    def test_bulk_edit_objects_select_all(self):
        """
        Bulk edit all Role instances.
        """
        self.add_permissions("extras.change_role", "extras.view_role")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.role_ct.id,
            edit_all=True,
            filter_query_params={},
            form_data={"color": "aa1409"},
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, Role.objects.all().count(), color="aa1409")

    def test_bulk_edit_objects_nullify(self):
        """
        Bulk edit Role instances to nullify their weight.
        """
        self.add_permissions("extras.change_role", "extras.view_role")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.role_ct.id,
            edit_all=True,
            filter_query_params={},
            form_data={"_nullify": ["weight"]},
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, Role.objects.all().count(), weight__isnull=True)

    def test_bulk_edit_select_some(self):
        """
        Bulk edit selected Namespace instances.
        """
        self.add_permissions("ipam.change_namespace", "ipam.view_namespace", "extras.change_tag", "extras.view_tag")
        namespaces = [Namespace.objects.create(name=f"Sample Namespace {x}") for x in range(5)]
        for namespace in namespaces:
            namespace.tags.set(self.tags[3:])
        pk_list = [str(status.id) for status in namespaces[:3]]

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.namespace_ct.id,
            edit_all=False,
            filter_query_params={},
            form_data={
                "pk": pk_list,
                "description": "Example description for bulk edit",
                "add_tags": [str(tag.id) for tag in self.tags[:3]],
                "remove_tags": [str(tag.id) for tag in self.tags[3:]],
            },
            username=self.user.username,
        )

        self._common_no_error_test_assertion(
            Namespace,
            job_result,
            3,
            description="Example description for bulk edit",
        )

        # Assert Namespaces within pk_list get updated tags
        for namespace in namespaces[:3]:
            self.assertTrue(namespace.tags.filter(pk__in=[tag.pk for tag in self.tags[:3]]).exists())
            self.assertFalse(namespace.tags.filter(pk__in=[tag.pk for tag in self.tags[3:]]).exists())

        # Assert Namespaces not within pk_list did not get updated tags
        for namespace in namespaces[3:]:
            self.assertFalse(namespace.tags.filter(pk__in=[tag.pk for tag in self.tags[:3]]).exists())
            self.assertTrue(namespace.tags.filter(pk__in=[tag.pk for tag in self.tags[3:]]).exists())

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.namespace_ct.id,
            edit_all=False,
            filter_query_params={},
            form_data={
                "pk": pk_list,
                "description": "Example description for bulk edit",
                "add_tags": [str(self.tags[0].id)],
                "remove_tags": [str(self.tags[-1].id)],
            },
            username=self.user.username,
        )

        self._common_no_error_test_assertion(
            Namespace,
            job_result,
            3,
            description="Example description for bulk edit",
        )

        # Assert Namespaces within pk_list get updated tag
        for namespace in namespaces[:3]:
            self.assertTrue(namespace.tags.filter(pk__in=[self.tags[0].pk]).exists())
            self.assertFalse(namespace.tags.filter(pk__in=[self.tags[-1].pk]).exists())

        # Assert Namespaces not within pk_list did not get updated tag
        for namespace in namespaces[3:]:
            self.assertFalse(namespace.tags.filter(pk__in=[self.tags[0].pk]).exists())
            self.assertTrue(namespace.tags.filter(pk__in=[self.tags[-1].pk]).exists())

    def test_bulk_edit_objects_filter_all(self):
        """
        Bulk edit all of the filtered Status instances.
        """
        self.add_permissions("extras.change_status", "extras.view_status")
        # By default Active and Available are some of the example of Status that starts with A
        statuses = Status.objects.filter(name__istartswith="A")
        status_to_ignore = Status.objects.create(name="Ignore Example Status")
        self.assertNotEqual(statuses.count(), 0)
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.status_ct.id,
            edit_all=True,
            filter_query_params={"name__isw": "A"},
            form_data={
                "color": "aa1409",
                "_all": "True",
            },
            username=self.user.username,
        )
        self._common_no_error_test_assertion(
            Status, job_result, statuses.count(), name__istartswith="A", color="aa1409"
        )
        self.assertNotEqual(status_to_ignore.color, "aa1409")

    def test_bulk_edit_objects_filter_some(self):
        """
        Bulk edit some of the filtered Status instances.
        """
        self.add_permissions("extras.change_status", "extras.view_status")
        # By default Active and Available are some of the example of Status that starts with A
        statuses = Status.objects.filter(name__istartswith="A")
        status_to_ignore = Status.objects.create(name="Ignore Example Status")
        self.assertNotEqual(statuses.count(), 0)
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.status_ct.id,
            edit_all=False,
            filter_query_params={"name__isw": "A", "sort": "name"},
            form_data={
                "pk": [str(statuses[0].pk)],
                "color": "aa1409",
            },
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Status, job_result, 1, name__istartswith="A", color="aa1409")
        self.assertNotEqual(status_to_ignore.color, "aa1409")

    def test_bulk_edit_objects_passing_in_both_pk_list_and_edit_all(self):
        """
        edit_all should override pk if both are passed.
        """
        self.add_permissions("extras.change_status", "extras.view_status")
        # By default Active and Available are some of the example of Status that starts with A
        statuses = Status.objects.filter(name__istartswith="A")
        status_to_ignore = Status.objects.create(name="Ignore Example Status")
        self.assertNotEqual(statuses.count(), 0)
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.status_ct.id,
            edit_all=True,
            filter_query_params={"name__isw": "A"},
            # pk ignored if edit_all is True
            form_data={
                "pk": [str(statuses[0].pk)],
                "color": "aa1409",
                "_all": "True",
            },
            username=self.user.username,
        )
        self._common_no_error_test_assertion(
            Status, job_result, statuses.count(), name__istartswith="A", color="aa1409"
        )
        self.assertNotEqual(status_to_ignore.color, "aa1409")

    def test_bulk_edit_objects_updating_the_same_field_as_the_filter_param(self):
        """
        Test bulk edit where the filter query param and the field to update are the same.
        e.g.
        form_data = {"status": "Test Deprecated"}
        filter_params = {"status": "Test Active"}
        """
        self.add_permissions("ipam.change_ipaddress", "extras.view_status")
        # By default Active and Available are some of the example of Status that starts with A
        active_status = Status.objects.create(name="Test Active")
        deprecated_status = Status.objects.create(name="Test Deprecated")
        active_status.content_types.add(self.ipaddress_ct)
        deprecated_status.content_types.add(self.ipaddress_ct)
        IPAddress.objects.all().update(status=active_status)
        self.assertEqual(IPAddress.objects.all().count(), IPAddress.objects.filter(status=active_status).count())

        # Update all IPAddresses with status=active_status to deprecated_statuses with no filters
        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.ipaddress_ct.id,
            edit_all=True,
            # pk ignored if edit_all is True
            form_data={
                "status": str(deprecated_status.pk),
                "_all": "True",
            },
            username=self.user.username,
        )
        self.assertEqual(IPAddress.objects.all().count(), IPAddress.objects.filter(status=deprecated_status).count())
        # Update all IPAddresses with status=active_status to deprecated_statuses with status filter applied
        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=self.ipaddress_ct.id,
            edit_all=True,
            filter_query_params={"status": "Test Deprecated"},
            # pk ignored if edit_all is True
            form_data={
                "status": str(active_status.pk),
                "per_page": 1,
                "_all": "True",
            },
            username=self.user.username,
        )
        self.assertEqual(IPAddress.objects.all().count(), IPAddress.objects.filter(status=active_status).count())


class BulkDeleteTestCase(TransactionTestCase):
    """
    Test the BulkDeleteObjects system job.
    """

    def setUp(self):
        super().setUp()
        self.status_ct = ContentType.objects.get_for_model(Status)
        self.role_ct = ContentType.objects.get_for_model(Role)
        for x in range(10):
            Status.objects.create(name=f"Example Status {x}")

        statuses = Status.objects.get_for_model(Circuit)
        circuit_type = CircuitType.objects.create(
            name="Example Circuit Type",
        )
        provider = Provider.objects.create(
            name="Example Provider",
        )

        Circuit.objects.create(
            cid="Circuit 1",
            provider=provider,
            circuit_type=circuit_type,
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=provider,
            circuit_type=circuit_type,
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 3",
            provider=provider,
            circuit_type=circuit_type,
            status=statuses[0],
        )

    def _common_no_error_test_assertion(self, model, job_result, **filter_params):
        self.assertJobResultStatus(job_result)
        self.assertEqual(model.objects.filter(**filter_params).count(), 0)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )

    def test_bulk_delete_objects_without_permission(self):
        statuses_to_delete = [str(status) for status in Status.objects.all().values_list("pk", flat=True)[:2]]
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.status_ct.id,
            pk_list=statuses_to_delete,
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        job_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(job_log.message, f'User "{self.user}" does not have permission to delete status objects')
        self.assertEqual(Status.objects.filter(pk__in=statuses_to_delete).count(), len(statuses_to_delete))

    def test_bulk_delete_objects_with_constrained_permission(self):
        statuses_to_delete = [str(status) for status in Status.objects.all().values_list("pk", flat=True)[:2]]
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": str(statuses_to_delete[0])},
            actions=["delete"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Status))

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.status_ct.id,
            pk_list=statuses_to_delete,
            username=self.user.username,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(
            error_log.message, "You do not have permissions to delete some of the objects provided in `pk_list`."
        )
        self.assertEqual(Status.objects.filter(pk__in=statuses_to_delete).count(), len(statuses_to_delete))

    def test_bulk_delete_objects_select_all(self):
        """
        Delete all Circuits objects.
        """
        self.add_permissions("circuits.delete_circuit")
        # Assert Circuit is not empty
        self.assertNotEqual(Circuit.objects.all().count(), 0)

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=ContentType.objects.get_for_model(Circuit).id,
            delete_all=True,
            filter_query_params={"per_page": 10},
            pk_list=[],
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Circuit, job_result)

    def test_bulk_delete_objects_select_some(self):
        """
        Delete some of the Role objects with no filter queries applied.
        """
        self.add_permissions("extras.delete_role")
        roles_to_delete = [Role.objects.create(name=f"Example Role {x}") for x in range(3)]
        roles_to_ignore = Role.objects.create(name="Ignore Example Role")
        roles_pks = [str(role.pk) for role in roles_to_delete]
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.role_ct.id,
            delete_all=False,
            filter_query_params={},
            pk_list=roles_pks,
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, pk__in=roles_pks)
        self.assertTrue(Role.objects.filter(name=roles_to_ignore.name).exists())

    def test_bulk_delete_objects_filter_all(self):
        """
        Delete all of the Status objects that start with "Example Status".
        """
        self.add_permissions("extras.delete_status")
        status_to_ignore = Status.objects.create(name="Ignore Example Status")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.status_ct.id,
            delete_all=True,
            filter_query_params={"name__isw": "Example Status", "sort": "name"},
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Status, job_result, name__istartswith="Example Status")
        self.assertTrue(Status.objects.filter(name=status_to_ignore.name).exists())

    def test_bulk_delete_objects_filter_some(self):
        """
        Delete some of the Role objects that start with "Example Status".
        """
        self.add_permissions("extras.delete_role")
        roles_to_delete = [Role.objects.create(name=f"Example Role {x}") for x in range(3)]
        roles_to_ignore = Role.objects.create(name="Ignore Example Role")
        roles_pks = [str(role.pk) for role in roles_to_delete]
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.role_ct.id,
            delete_all=False,
            filter_query_params={"name__isw": "Example Status"},
            pk_list=roles_pks,
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, pk__in=roles_pks)
        self.assertTrue(Role.objects.filter(name=roles_to_ignore.name).exists())

    def test_bulk_delete_objects_passing_both_pk_list_and_delete_all(self):
        """
        delete_all should override pk_list if both are passed.
        """
        self.add_permissions("extras.delete_status")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            content_type=self.status_ct.pk,
            delete_all=True,
            filter_query_params={"name__isw": "Example Status", "sort": "name"},
            pk_list=[str(Status.objects.first().pk)],
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Role, job_result, name__istartswith="Example Status")
