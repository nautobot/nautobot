from pathlib import Path

from django.contrib.contenttypes.models import ContentType
import yaml

from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.dcim.models import DeviceType, Manufacturer
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import ExportTemplate, JobLogEntry, Status
from nautobot.users.models import ObjectPermission


class ExportObjectListTest(TransactionTestCase):
    """
    Test the ExportObjectList system job.
    """

    databases = ("default", "job_logs")

    def test_export_without_permission(self):
        """Job should enforce user permissions on the content-type being asked for export."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_statuses.csv")
        csv_data = job_result.files.first().file.read().decode("utf-8")
        self.assertIn(str(instance1.pk), csv_data)
        self.assertNotIn(str(instance2.pk), csv_data)

    def test_export_all_to_csv(self):
        """By default, job should export all instances to CSV."""
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(Status).pk,
        )
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_device_types.yaml")
        yaml_data = job_result.files.first().file.read().decode("utf-8")
        data = yaml.safe_load(yaml_data)
        self.assertEqual(data["manufacturer"], "Cisco")


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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)

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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
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
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING).exists()
        )
        self.assertFalse(
            JobLogEntry.objects.filter(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR).exists()
        )
        self.assertEqual(4, Status.objects.filter(name__startswith="test_status").count())

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
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
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
            self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_FAILURE)
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
