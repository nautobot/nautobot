import codecs
from datetime import timedelta
import json
import logging
from pathlib import Path
from unittest import mock
import uuid
import weakref

from constance.test import override_config
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import ManyToOneRel
from django.db.models.signals import pre_delete
from django.test import tag
from django.utils import timezone
import time_machine
import yaml

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.celery.encoders import NautobotKombuJSONEncoder
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE
from nautobot.core.jobs import DeleteCustomFieldData, ExportObjectList, UpdateCustomFieldChoiceData
from nautobot.core.jobs.archive import _iterate_records_by_timestamp, ArchiveOldRecords, FORCE_CASCADE_DELETE_HINT
from nautobot.core.jobs.cleanup import CleanupTypes
from nautobot.core.jobs.deletion_utils import (
    _describe_reference_path,
    exclude_records_whose_relations_block_deletion,
    find_relations_of_concern,
)
from nautobot.core.testing import create_job_result_and_run_job, TestCase, TransactionTestCase
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.dcim.models import DeviceType, FrontPortTemplate, Interface, LocationType, Manufacturer
from nautobot.extras.choices import (
    DynamicGroupTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
    MetadataTypeDataTypeChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.factory import JobResultFactory, LIVE_HISTORY_END, LIVE_HISTORY_START, ObjectChangeFactory
from nautobot.extras.jobs import RunJobTaskFailed
from nautobot.extras.models import (
    ArchivedJobConsoleEntry,
    ArchivedJobLogEntry,
    ArchivedJobResult,
    ArchivedObjectChange,
    DynamicGroup,
    ExportTemplate,
    FileProxy,
    Job,
    JobButton,
    JobConsoleEntry,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Role,
    SavedView,
    Status,
    Tag,
)
from nautobot.extras.models.metadata import MetadataType, ObjectMetadata
from nautobot.extras.signals import _handle_deleted_object
from nautobot.ipam.models import IPAddress, Namespace
from nautobot.users.models import ObjectPermission, Token, User


class ExportObjectListTest(TransactionTestCase):
    """
    Test the ExportObjectList system job.

    Which objects an export covers and which fields it carries -- the query string's filters and sort
    order, saved views, and the field selection -- is covered by `test_import_export`, whose
    `ImportExportJobTestCase` harness reads the produced file back.
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
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(log_error.message, f'User "{self.user}" does not have permission to view status objects')
        self.assertFalse(job_result.files.exists())

    def test_export_content_type_without_a_model(self):
        """A content type whose model is gone fails with an explanatory error, not an AttributeError.

        A ContentType row outlives the app that declared its model, so `model_class()` returning None is
        a state a user can reach by uninstalling an App and then exporting from a stale bookmark.
        """
        content_type = ContentType.objects.create(app_label="nonexistent_app", model="nonexistentmodel")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=content_type.pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(
            JobLogEntry.objects.filter(
                job_result=job_result,
                message__contains="Could not find the",
                log_level=LogLevelChoices.LOG_ERROR,
            ).exists()
        )
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

    def test_tokens_are_never_imported_or_exported(self):
        """Neither Job handles Tokens, even for a superuser, as the Tokens' keys would be written to a file."""
        superuser = User.objects.create_user(username="token-superuser", is_superuser=True)
        Token.objects.create(user=superuser)
        for action, job_class_name, kwargs in (
            ("export", "ExportObjectList", {}),
            ("import", "ImportObjects", {"csv_data": "description\nImported Token"}),
        ):
            with self.subTest(job_class_name=job_class_name):
                job_result = create_job_result_and_run_job(
                    "nautobot.core.jobs",
                    job_class_name,
                    username=superuser.username,
                    content_type=ContentType.objects.get_for_model(Token).pk,
                    **kwargs,
                )
                self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
                self.assertTrue(
                    JobLogEntry.objects.filter(
                        job_result=job_result,
                        log_level=LogLevelChoices.LOG_ERROR,
                        message=f"users.token objects do not support {action}",
                    ).exists()
                )
                self.assertFalse(job_result.files.exists())
        self.assertFalse(Token.objects.filter(description="Imported Token").exists())

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

    def test_export_json_keeps_real_nulls_and_literal_sentinel_strings(self):
        """The JSON document carries real nulls, so a value that is literally "NULL" is not mistaken for one.

        CSV must spell a null with the in-band CSV_NULL_TYPE sentinel; routing JSON/YAML through that
        representation used to make the two indistinguishable and silently null out the string.
        """
        status = Status.objects.create(name="Export Null Probe", description=CSV_NULL_TYPE)
        status.content_types.add(ContentType.objects.get_for_model(Status))
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs",
            "ExportObjectList",
            content_type=ContentType.objects.get_for_model(Status).pk,
            export_format="json",
            query_string="name=Export+Null+Probe",
        )
        self.assertJobResultStatus(job_result)
        record = json.loads(job_result.files.first().file.read().decode("utf-8"))["records"][0]
        self.assertEqual(record["description"], CSV_NULL_TYPE)
        # ...and no relation is reported with the CSV "no object" sentinel; absent ones are real nulls
        self.assertNotIn(CSV_NO_OBJECT, json.dumps(record))

    def test_export_devicetype_to_devicetype_library_yaml(self):
        """Export device-type to the devicetype-library interchange format, which is now explicitly chosen."""
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
            export_format="devicetype_library",
        )
        self.assertJobResultStatus(job_result)
        self.assertTrue(job_result.files.exists())
        self.assertEqual(Path(job_result.files.first().file.name).name, "nautobot_device_types.yaml")
        yaml_data = job_result.files.first().file.read().decode("utf-8")
        data = yaml.safe_load(yaml_data)
        self.assertEqual(data["manufacturer"], "Cisco")

    def test_object_var_lookup_must_be_permitted(self):
        """An `ObjectVar` given as a dict of attributes (as the REST API accepts) may only use permitted lookups.

        Otherwise, whether the Job is accepted would reveal data such as another user's API token, reached here
        through the users of the object permissions for a content type.
        """
        content_type = ContentType.objects.get_for_model(Status)
        self.assertEqual(
            ExportObjectList.deserialize_data({"content_type": {"app_label": "extras", "model": "status"}}),
            {"content_type": content_type},
        )
        for lookup in (
            {"app_label": "extras", "model__startswith": "stat"},
            {"app_label": "extras", "model": "status", "object_permissions__users__tokens__key__startswith": "a"},
        ):
            with self.subTest(lookup=lookup):
                with self.assertRaisesRegex(ValidationError, "is not a permitted lookup"):
                    ExportObjectList.deserialize_data({"content_type": lookup})


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
        # To avoid spurious test failures due to factory randomness,
        # ensure that we have some records well outside the test data cutoff windows.
        # The newest are at the end of the factories' live history rather than after it, so that none is in the future:
        # tests that run with `max_age=0` against the current time expect the newest records to be old enough to delete.
        before_live_history = LIVE_HISTORY_START - timedelta(days=365)
        ObjectChangeFactory.create(time=before_live_history)
        ObjectChangeFactory.create(time=LIVE_HISTORY_END)
        latest_jr = JobResult.objects.latest()
        latest_jr.date_created = latest_jr.date_started = latest_jr.date_done = LIVE_HISTORY_END
        latest_jr.save()
        earliest_jr = JobResult.objects.earliest()
        earliest_jr.date_created = earliest_jr.date_started = earliest_jr.date_done = before_live_history
        earliest_jr.save()

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
        # Everything deleted along with a job result or object change must be permitted to the user too.
        self.add_permissions(
            "extras.delete_joblogentry",
            "extras.delete_jobconsoleentry",
            "extras.delete_objectmetadata",
            "extras.delete_fileproxy",
        )
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
        # Late in the factories' live history, so there are records on both sides of the cutoff.
        with time_machine.travel(LIVE_HISTORY_END - timedelta(days=92)):
            cutoff = timezone.now() - timedelta(days=60)
            job_results_to_be_deleted = JobResult.objects.filter(date_done__lt=cutoff)
            job_results_to_be_deleted_count = job_results_to_be_deleted.count()
            job_log_entry_to_be_deleted_count = JobLogEntry.objects.filter(
                job_result__in=job_results_to_be_deleted
            ).count()
            job_console_entry_to_be_deleted_count = JobConsoleEntry.objects.filter(
                job_result__in=job_results_to_be_deleted
            ).count()
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
            if job_console_entry_to_be_deleted_count > 0:
                started_logs["job_output"]["extras.JobConsoleEntry"] = job_console_entry_to_be_deleted_count
            if objectmetadata_to_be_deleted_count > 0:
                started_logs["job_output"]["extras.ObjectMetadata"] = objectmetadata_to_be_deleted_count

            self.assertEqual(
                cm.output[1],
                f"INFO:nautobot.events.nautobot.jobs.job.completed:{json.dumps(started_logs, indent=4)}",
            )

    def test_cleanup_object_changes(self):
        """With unconstrained permissions, all ObjectChanges before the cutoff should be deleted."""
        # Late in the factories' live history, so there are records on both sides of the cutoff.
        with time_machine.travel(LIVE_HISTORY_END - timedelta(days=92)):
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

    def make_old_job_result_with_log_entry(self):
        """Create a `JobResult` that finished long before any cutoff the tests use, with one log entry."""
        old_job_result = JobResult.objects.create(
            name="Cleanup Test Job",
            task_name="nautobot.core.tests.test_jobs.cleanup_test_job",
            user=self.user,
            status=JobResultStatusChoices.STATUS_SUCCESS,
        )
        old_job_result.date_done = LIVE_HISTORY_START - timedelta(days=365)
        old_job_result.save()
        log_entry = JobLogEntry.objects.create(
            job_result=old_job_result, log_level=LogLevelChoices.LOG_INFO, grouping="main", message="cleanup test"
        )
        return old_job_result, log_entry

    def test_a_user_without_delete_permission_on_log_entries_fails_the_job(self):
        """
        Deleting a job result deletes its log and console entries.

        The job therefore checks for permission to delete both models before it deletes anything.
        """
        self.add_permissions("extras.delete_jobresult")
        old_job_result, _ = self.make_old_job_result_with_log_entry()

        cleanup_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            username=self.user.username,
            cleanup_types=[CleanupTypes.JOB_RESULT],
            max_age=60,
        )

        self.assertJobResultStatus(cleanup_job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertIn(
            f'User "{self.user}" does not have permission to delete JobLogEntry records',
            cleanup_job_result.job_log_entries.values_list("message", flat=True),
        )

    def test_a_job_result_with_log_entries_the_user_cannot_delete_is_not_deleted(self):
        """Deleting the job result would delete log entries that the user is not permitted to delete."""
        self.add_permissions("extras.delete_jobresult", "extras.delete_jobconsoleentry")
        held_job_result, held_log_entry = self.make_old_job_result_with_log_entry()
        permitted_job_result, permitted_log_entry = self.make_old_job_result_with_log_entry()
        self.add_permissions("extras.delete_joblogentry", constraints={"pk__in": [str(permitted_log_entry.pk)]})

        cleanup_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            username=self.user.username,
            cleanup_types=[CleanupTypes.JOB_RESULT],
            max_age=60,
        )

        self.assertJobResultStatus(cleanup_job_result)
        self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertTrue(JobLogEntry.objects.filter(pk=held_log_entry.pk).exists())
        self.assertFalse(JobResult.objects.filter(pk=permitted_job_result.pk).exists())
        job_log_messages = list(cleanup_job_result.job_log_entries.values_list("message", flat=True))
        # The factory job results from `setUp` have log entries the user may not delete either, so the counts in the
        # messages are not asserted.
        self.assertTrue(
            any(
                message.startswith("Skipping ")
                and message.endswith(
                    "JobResult records whose deletion would also delete the extras.JobLogEntry records that reference"
                    f" them through extras.JobLogEntry.job_result. User {self.user} is not permitted to delete those"
                    " extras.JobLogEntry records."
                )
                for message in job_log_messages
            ),
            job_log_messages,
        )
        self.assertTrue(any(message.startswith("Omitting ") for message in job_log_messages), job_log_messages)

    def test_job_results_are_deleted_across_several_batches(self):
        """Each batch is read after the previous one is deleted, so paging must not skip or repeat records."""
        old_job_results = [self.make_old_job_result_with_log_entry()[0] for _ in range(3)]
        for old_job_result in old_job_results:
            JobLogEntry.objects.create(
                job_result=old_job_result, log_level=LogLevelChoices.LOG_INFO, grouping="main", message="second"
            )
        old_job_result_pks = [old_job_result.pk for old_job_result in old_job_results]
        cutoff_job_results = JobResult.objects.filter(date_done__lt=timezone.now() - timedelta(days=60))
        expected_job_result_count = cutoff_job_results.count()
        expected_log_entry_count = JobLogEntry.objects.filter(job_result__in=cutoff_job_results).count()

        with mock.patch("nautobot.core.jobs.cleanup.CLEANUP_BATCH_SIZE", 1):
            cleanup_job_result = create_job_result_and_run_job(
                "nautobot.core.jobs.cleanup",
                "LogsCleanup",
                cleanup_types=[CleanupTypes.JOB_RESULT],
                max_age=60,
            )

        self.assertJobResultStatus(cleanup_job_result)
        self.assertFalse(JobResult.objects.filter(pk__in=old_job_result_pks).exists())
        self.assertFalse(JobLogEntry.objects.filter(job_result_id__in=old_job_result_pks).exists())
        self.assertEqual(cleanup_job_result.result["extras.JobResult"], expected_job_result_count)
        self.assertEqual(cleanup_job_result.result["extras.JobLogEntry"], expected_log_entry_count)

    # The example_app models below are imported inside each test because example_app is an optional app: the
    # module must still import when it is not installed, and the `example_app` tag skips these tests then.
    @tag("example_app")
    def test_a_job_result_whose_log_entry_is_restricted_is_not_deleted(self):
        """
        Deleting the job result would cascade to the log entry, which a `RESTRICT` reference forbids.

        The job result and its log entry are left in place, and the other old job results are still deleted.
        """
        from example_app.models import AnotherExampleModel

        held_job_result, held_log_entry = self.make_old_job_result_with_log_entry()
        AnotherExampleModel.objects.create(name="Cleanup Restrict Probe", job_log_entry=held_log_entry)
        free_job_result, _ = self.make_old_job_result_with_log_entry()

        cleanup_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            cleanup_types=[CleanupTypes.JOB_RESULT],
            max_age=60,
        )

        self.assertJobResultStatus(cleanup_job_result)
        self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertTrue(JobLogEntry.objects.filter(pk=held_log_entry.pk).exists())
        self.assertFalse(JobResult.objects.filter(pk=free_job_result.pk).exists())
        self.assertTrue(
            any(
                message.startswith("Skipping 1 JobResult records")
                for message in cleanup_job_result.job_log_entries.values_list("message", flat=True)
            )
        )

    @tag("example_app")
    def test_records_with_many_to_many_links_are_deleted_with_their_links(self):
        """
        A record that cascades from a job result is deleted together with its many-to-many links, in both directions.

        Regression test for #9639, where the links were left behind and the run failed on a foreign key violation.
        """
        from example_app.models import ExampleModel

        old_job_result, log_entry = self.make_old_job_result_with_log_entry()
        cascading_record = ExampleModel.objects.create(name="Cleanup M2M Probe", job_log_entry=log_entry)
        linked_record = ExampleModel.objects.create(name="Cleanup M2M Linked Probe")
        cascading_record.linked_example_models.add(linked_record)
        linked_record.linked_example_models.add(cascading_record)

        cleanup_job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.cleanup",
            "LogsCleanup",
            cleanup_types=[CleanupTypes.JOB_RESULT],
            max_age=60,
        )

        self.assertJobResultStatus(cleanup_job_result)
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertFalse(ExampleModel.objects.filter(pk=cascading_record.pk).exists())
        self.assertTrue(ExampleModel.objects.filter(pk=linked_record.pk).exists())
        self.assertFalse(linked_record.linked_example_models.exists())
        self.assertFalse(linked_record.linking_example_models.exists())


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
        for tag_object in self.tags:
            tag_object.content_types.add(self.namespace_ct)

    def _common_no_error_test_assertion(self, model, job_result, expected_count, **filter_params):
        self.assertJobResultStatus(job_result)
        self.assertEqual(model.objects.filter(**filter_params).count(), expected_count)
        warning_or_error_logs = JobLogEntry.objects.filter(
            job_result=job_result, log_level__in=[LogLevelChoices.LOG_WARNING, LogLevelChoices.LOG_ERROR]
        )
        self.assertFalse(warning_or_error_logs.exists(), list(warning_or_error_logs.values_list("message", flat=True)))

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
            filter_query_params={"per_page": [2]},
            pk_list=pk_list,
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
            pk_list=pk_list,
            filter_query_params={"sort": ["name"]},
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

    def test_bulk_edit_objects_select_all_prefetch_related(self):
        """
        Bulk edit all DeviceType instances (https://github.com/nautobot/nautobot/issues/8570).
        """
        self.add_permissions("dcim.change_devicetype", "dcim.view_devicetype")
        mfr = Manufacturer.objects.create(name="Cisco")
        for x in range(3):
            DeviceType.objects.create(manufacturer=mfr, model=f"Cisco CSR{x}000v")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=ContentType.objects.get_for_model(DeviceType).id,
            edit_all=True,
            filter_query_params={},
            form_data={"u_height": 0},
            username=self.user.username,
        )
        self._common_no_error_test_assertion(DeviceType, job_result, DeviceType.objects.all().count(), u_height=0)

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
            pk_list=pk_list,
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

    def test_bulk_edit_objects_kubernetes_serialization_nested_models(self):
        """
        Regression test for Kubernetes job execution.

        Kubernetes stores job kwargs (including BulkEdit `form_data`) in a JSONField, which uses
        NautobotKombuJSONEncoder to serialize Django model instances into `__nautobot_type__` dicts.
        `BulkEditObjects.serialize_data()` must recursively pre-flatten any nested models into primitive PK values,
        otherwise BulkEdit's form validation will fail with `invalid_list`.
        """

        self.add_permissions("ipam.change_namespace", "ipam.view_namespace", "extras.change_tag", "extras.view_tag")

        namespaces = [Namespace.objects.create(name=f"Sample Namespace {x}") for x in range(2)]
        for namespace in namespaces:
            namespace.tags.set(self.tags[2:])

        pk_list = [str(ns.pk) for ns in namespaces]
        add_tags = self.tags[:2]

        # Mimic the UI job enqueue payload: include actual model instances inside form_data.
        job_kwargs = {
            "content_type": self.namespace_ct,
            "edit_all": False,
            "filter_query_params": {},
            "pk_list": pk_list,
            "form_data": {"pk": namespaces, "add_tags": add_tags},
        }

        from nautobot.core.jobs.bulk_actions import BulkEditObjects

        serialized_job_kwargs = BulkEditObjects.serialize_data(job_kwargs)
        # Mimic the Kubernetes JSONField encoding of task_kwargs.
        encoded_job_kwargs = json.loads(json.dumps(serialized_job_kwargs, cls=NautobotKombuJSONEncoder))

        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            content_type=encoded_job_kwargs["content_type"],
            edit_all=encoded_job_kwargs["edit_all"],
            filter_query_params=encoded_job_kwargs["filter_query_params"],
            pk_list=encoded_job_kwargs["pk_list"],
            form_data=encoded_job_kwargs["form_data"],
            username=self.user.username,
        )

        self._common_no_error_test_assertion(Namespace, job_result, 2, pk__in=pk_list)

        # Assert namespaces received the added tags.
        add_tag_pks = [tag.pk for tag in add_tags]
        for namespace in namespaces:
            self.assertTrue(namespace.tags.filter(pk__in=add_tag_pks).exists())

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
            edit_all=True,
            filter_query_params={"name__isw": ["A"], "sort": ["name"]},
            pk_list=[str(statuses[0].pk)],
            form_data={
                "pk": [str(statuses[0].pk)],
                "color": "aa1409",
            },
            username=self.user.username,
        )
        self._common_no_error_test_assertion(Status, job_result, len(statuses), name__istartswith="A", color="aa1409")
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
            filter_query_params={"name__isw": ["A"]},
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

    def test_bulk_edit_objects_with_saved_view(self):
        """
        Bulk edit Status objects using a SavedView filter.
        """
        self.add_permissions("extras.change_status", "extras.view_status")
        saved_view = SavedView.objects.create(
            name="Save View for Statuses",
            owner=self.user,
            view="extras:status_list",
            config={"filter_params": {"name__isw": ["A"]}},
        )

        # Confirm the SavedView filter matches some but not all Statuses
        self.assertTrue(
            0 < saved_view.get_filtered_queryset(self.user).count() < Status.objects.exclude(color="aa1409").count()
        )
        delta_count = (
            Status.objects.exclude(color="aa1409").count() - saved_view.get_filtered_queryset(self.user).count()
        )

        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            username=self.user.username,
            content_type=self.status_ct.id,
            edit_all=True,
            filter_query_params={},
            pk_list=[],
            saved_view_id=saved_view.id,
            form_data={"color": "aa1409", "_all": "True"},
        )

        self.assertEqual(delta_count, Status.objects.exclude(color="aa1409").count())

    def test_bulk_edit_objects_with_saved_view_with_all_filters_removed(self):
        """
        Bulk edit Status objects using a SavedView filter but overwriting the saved field.
        """
        self.add_permissions("extras.change_status", "extras.view_status")
        saved_view = SavedView.objects.create(
            name="Save View for Statuses",
            owner=self.user,
            view="extras:status_list",
            config={"filter_params": {"name__isw": ["A"]}},
        )

        self.assertTrue(
            0 < saved_view.get_filtered_queryset(self.user).count() < Status.objects.exclude(color="aa1409").count()
        )

        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkEditObjects",
            username=self.user.username,
            content_type=self.status_ct.id,
            edit_all=True,
            filter_query_params={"all_filters_removed": [True]},
            pk_list=[],
            saved_view_id=saved_view.id,
            form_data={"color": "aa1409", "_all": "True"},
        )

        self.assertEqual(0, Status.objects.exclude(color="aa1409").count())


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
        Circuit.objects.create(
            cid="Not Circuit",
            provider=provider,
            circuit_type=circuit_type,
            status=statuses[0],
        )

        self.saved_view = SavedView.objects.create(
            name="Save View for Circuits",
            owner=self.user,
            view="circuits:circuit_list",
            config={"filter_params": {"cid__isw": "Circuit "}},
        )

    def _common_no_error_test_assertion(self, model, job_result, **filter_params):
        self.assertJobResultStatus(job_result)
        self.assertEqual(model.objects.filter(**filter_params).count(), 0)
        warning_or_error_logs = JobLogEntry.objects.filter(
            job_result=job_result, log_level__in=[LogLevelChoices.LOG_WARNING, LogLevelChoices.LOG_ERROR]
        )
        self.assertFalse(warning_or_error_logs.exists(), list(warning_or_error_logs.values_list("message", flat=True)))

    def test_bulk_delete_objects_without_permission(self):
        statuses_to_delete = [str(status) for status in Status.objects.all().values_list("pk", flat=True)[:2]]
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            username=self.user.username,
            content_type=self.status_ct.id,
            delete_all=False,
            filter_query_params={},
            pk_list=statuses_to_delete,
            saved_view_id=None,
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
            username=self.user.username,
            content_type=self.status_ct.id,
            delete_all=False,
            filter_query_params={},
            pk_list=statuses_to_delete,
            saved_view_id=None,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        error_log = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertIn("Cannot delete some instances of model", error_log.message)
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
            username=self.user.username,
            content_type=ContentType.objects.get_for_model(Circuit).id,
            delete_all=True,
            filter_query_params={"per_page": [10]},
            pk_list=[],
            saved_view_id=None,
        )
        self._common_no_error_test_assertion(Circuit, job_result)

    def test_bulk_delete_objects_select_all_prefetch_related(self):
        """
        Delete all DeviceType objects (https://github.com/nautobot/nautobot/issues/8570).
        """
        self.add_permissions("dcim.delete_devicetype", "dcim.view_devicetype")
        mfr = Manufacturer.objects.create(name="Cisco")
        for x in range(3):
            DeviceType.objects.create(manufacturer=mfr, model=f"Cisco CSR{x}000v")
        job_result = create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            username=self.user.username,
            content_type=ContentType.objects.get_for_model(DeviceType).id,
            delete_all=True,
            filter_query_params={"per_page": [10]},
            pk_list=[],
            saved_view_id=None,
        )
        self._common_no_error_test_assertion(DeviceType, job_result)

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
            username=self.user.username,
            content_type=self.role_ct.id,
            delete_all=False,
            filter_query_params={},
            pk_list=roles_pks,
            saved_view_id=None,
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
            username=self.user.username,
            content_type=self.status_ct.id,
            delete_all=True,
            filter_query_params={"name__isw": ["Example Status"], "sort": ["name"]},
            pk_list=[],
            saved_view_id=None,
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
            username=self.user.username,
            content_type=self.role_ct.id,
            delete_all=False,
            filter_query_params={"name__isw": ["Example Status"]},
            pk_list=roles_pks,
            saved_view_id=None,
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
            username=self.user.username,
            content_type=self.status_ct.pk,
            delete_all=True,
            filter_query_params={"name__isw": ["Example Status"]},
            pk_list=[str(Status.objects.first().pk)],
            saved_view_id=None,
        )
        self._common_no_error_test_assertion(Role, job_result, name__istartswith="Example Status")

    def test_bulk_delete_objects_with_saved_view(self):
        """
        Delete objects using a SavedView filter.
        """
        self.add_permissions("circuits.delete_circuit", "circuits.view_circuit")

        # we assert that the saved view filter actually filters some circuits and there are others not filtered out
        self.assertTrue(0 < self.saved_view.get_filtered_queryset(self.user).count() < Circuit.objects.all().count())
        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            username=self.user.username,
            content_type=ContentType.objects.get_for_model(Circuit).id,
            delete_all=True,
            filter_query_params={},
            pk_list=[],
            saved_view_id=self.saved_view.id,
        )
        self.assertTrue(Circuit.objects.exists())
        self.assertFalse(self.saved_view.get_filtered_queryset(self.user).exists())

    def test_bulk_delete_objects_with_saved_view_with_all_filters_removed(self):
        """
        Delete Objects using a SavedView filter, but ignore the filter if all_filters_removed is set.
        """
        self.add_permissions("circuits.delete_circuit", "circuits.view_circuit")

        # we assert that the saved view filter actually filters some circuits and there are others not filtered out
        self.assertTrue(0 < self.saved_view.get_filtered_queryset(self.user).count() < Circuit.objects.all().count())
        create_job_result_and_run_job(
            "nautobot.core.jobs.bulk_actions",
            "BulkDeleteObjects",
            username=self.user.username,
            content_type=ContentType.objects.get_for_model(Circuit).id,
            delete_all=True,
            filter_query_params={"all_filters_removed": [True]},
            pk_list=[],
            saved_view_id=self.saved_view.id,
        )
        self.assertFalse(Circuit.objects.all().exists())


class RefreshDynamicGroupCacheJobButtonReceiverTestCase(TransactionTestCase):
    job_module = "nautobot.core.jobs.groups"
    job_name = "RefreshDynamicGroupCacheJobButtonReceiver"

    def test_successful_cache_refresh(self):
        LocationType.objects.create(name="DG Test LT 1")
        LocationType.objects.create(name="DG Test LT 2")
        LocationType.objects.create(name="DG Test LT 3")
        dg = DynamicGroup(
            name="Location Types",
            content_type=ContentType.objects.get_for_model(LocationType),
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
            filter={"name__isw": ["DG Test"]},
        )
        dg.clean()
        dg.save(update_cached_members=False)
        self.assertEqual(0, dg.count)

        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            object_model_name="extras.dynamicgroup",
            object_pk=dg.pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(3, dg.count)

        dg.filter = {"name__iew": ["DG Test"]}
        dg.clean()
        dg.save(update_cached_members=False)
        self.assertEqual(3, dg.count)
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            object_model_name="extras.dynamicgroup",
            object_pk=dg.pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(0, dg.count)

    def test_failure_on_non_dg(self):
        """The job's buttons only apply to dynamic groups, so any other object is refused before the job sees it."""
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            object_model_name="extras.status",
            object_pk=Status.objects.first().pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_error = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_ERROR)
        self.assertEqual(log_error.message, "No enabled job button for this job applies to extras.status objects")

    def test_failure_on_non_dg_with_a_button(self):
        """Should a button nonetheless apply the job to another type of object, the job itself refuses it."""
        job_button = JobButton.objects.create(
            name="Refresh Statuses",
            text="Refresh",
            job=Job.objects.get_for_class_path(f"{self.job_module}.{self.job_name}"),
        )
        job_button.content_types.add(ContentType.objects.get_for_model(Status))
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            object_model_name="extras.status",
            object_pk=Status.objects.first().pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_fail = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_FAILURE)
        self.assertEqual(log_fail.message, "This job button should only be used with Dynamic Group records.")

    def test_failure_on_static_dg(self):
        dg = DynamicGroup.objects.create(
            name="Location Types",
            content_type=ContentType.objects.get_for_model(LocationType),
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            object_model_name="extras.dynamicgroup",
            object_pk=dg.pk,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_fail = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_FAILURE)
        self.assertEqual(
            log_fail.message,
            "The members of this Dynamic Group are statically defined and do not need to be recalculated.",
        )


class ValidateModelDataTestCase(TransactionTestCase):
    job_module = "nautobot.core.jobs"
    job_name = "ValidateModelData"

    def test_successful_validation(self):
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            content_types=[ContentType.objects.get_for_model(Status).pk],
            verbose=True,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)

    def test_failure_on_invalid_dg(self):
        dg = DynamicGroup(
            name="Legacy rear_port_template filter",
            filter={"rear_port_template": "74aac78c-fabb-468c-a036-26c46c56f27a"},
            content_type=ContentType.objects.get_for_model(FrontPortTemplate),
        )
        dg.save(update_cached_members=False)
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            content_types=[ContentType.objects.get_for_model(DynamicGroup).pk],
            verbose=False,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_fail = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_FAILURE)
        self.assertIn("Enter a list of values", log_fail.message)

    def test_warning_without_permission(self):
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_types=[ContentType.objects.get_for_model(Status).pk],
            verbose=True,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)
        log_warn = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_WARNING)
        self.assertEqual("No statuses found", log_warn.message)
        self.assertIsNone(
            JobLogEntry.objects.filter(
                job_result=job_result, log_level=LogLevelChoices.LOG_SUCCESS, message="Validated successfully"
            ).first()
        )

    def test_no_restrict_superuser(self):
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            content_types=[ContentType.objects.get_for_model(User).pk],
            verbose=True,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)

    def test_no_restrict_non_superuser(self):
        job_result = create_job_result_and_run_job(
            self.job_module,
            self.job_name,
            username=self.user.username,  # otherwise run_job_for_testing defaults to a superuser account
            content_types=[ContentType.objects.get_for_model(User).pk],
            verbose=True,
        )
        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        log_fail = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_FAILURE)
        self.assertIn("Unable to apply access permissions to users.user", log_fail.message)


class DeleteCustomFieldDataTest(TransactionTestCase):
    """Test input normalization/validation in DeleteCustomFieldData.run()."""

    def setUp(self):
        super().setUp()
        self.job = DeleteCustomFieldData()
        self.job.logger = logging.getLogger("test")

    @mock.patch("nautobot.extras.customfields.delete_custom_field_data")
    def test_field_specs_valid_json(self, mock_fn):
        self.job.run(field_specs='[{"field_key": "k", "content_types": ["ct1"]}]')
        mock_fn.assert_called_once_with(
            field_key="k", content_type_pk_set=["ct1"], verbose=False, job_logger=self.job.logger
        )

    @mock.patch("nautobot.extras.customfields.delete_custom_field_data")
    def test_field_specs_multiple_items(self, mock_fn):
        specs = json.dumps(
            [
                {"field_key": "k1", "content_types": ["ct1"]},
                {"field_key": "k2", "content_types": ["ct2", "ct3"]},
            ]
        )
        self.job.run(field_specs=specs)
        self.assertEqual(mock_fn.call_count, 2)
        mock_fn.assert_any_call(field_key="k1", content_type_pk_set=["ct1"], verbose=False, job_logger=self.job.logger)
        mock_fn.assert_any_call(
            field_key="k2", content_type_pk_set=["ct2", "ct3"], verbose=False, job_logger=self.job.logger
        )

    def test_field_specs_invalid_json(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs="not json")

    def test_field_specs_not_a_list(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs='{"field_key": "k"}')

    def test_field_specs_bad_item_schema(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs='[{"wrong_key": 1}]')

    @mock.patch("nautobot.extras.customfields.delete_custom_field_data")
    def test_fallback_to_single_spec(self, mock_fn):
        ct = mock.Mock()
        ct.pk = "fake-pk"
        self.job.run(field_key="my_key", content_types=[ct])
        mock_fn.assert_called_once_with(
            field_key="my_key", content_type_pk_set=["fake-pk"], verbose=False, job_logger=self.job.logger
        )

    def test_no_input_raises(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run()


class UpdateCustomFieldChoiceDataTest(TransactionTestCase):
    """Test input normalization/validation in UpdateCustomFieldChoiceData.run()."""

    def setUp(self):
        super().setUp()
        self.job = UpdateCustomFieldChoiceData()
        self.job.logger = logging.getLogger("test")

    @mock.patch("nautobot.extras.customfields.update_custom_field_choice_data")
    def test_field_specs_valid_json(self, mock_fn):
        self.job.run(field_specs='[{"field_id": "f1", "old_value": "old", "new_value": "new"}]')
        mock_fn.assert_called_once_with(field_id="f1", old_value="old", new_value="new", job_logger=self.job.logger)

    @mock.patch("nautobot.extras.customfields.update_custom_field_choice_data")
    def test_field_specs_multiple_items(self, mock_fn):
        specs = json.dumps(
            [
                {"field_id": "f1", "old_value": "a", "new_value": "b"},
                {"field_id": "f2", "old_value": "c", "new_value": "d"},
            ]
        )
        self.job.run(field_specs=specs)
        self.assertEqual(mock_fn.call_count, 2)
        mock_fn.assert_any_call(field_id="f1", old_value="a", new_value="b", job_logger=self.job.logger)
        mock_fn.assert_any_call(field_id="f2", old_value="c", new_value="d", job_logger=self.job.logger)

    def test_field_specs_invalid_json(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs="not json")

    def test_field_specs_not_a_list(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs='{"field_id": "f1"}')

    def test_field_specs_bad_item_schema(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run(field_specs='[{"wrong_key": 1}]')

    @mock.patch("nautobot.extras.customfields.update_custom_field_choice_data")
    def test_fallback_to_single_spec(self, mock_fn):
        field = mock.Mock()
        field.pk = "fake-field-pk"
        self.job.run(field=field, old_value="old", new_value="new")
        mock_fn.assert_called_once_with(
            field_id="fake-field-pk", old_value="old", new_value="new", job_logger=self.job.logger
        )

    def test_no_input_raises(self):
        with self.assertRaises(RunJobTaskFailed):
            self.job.run()


ARCHIVE_AGE_THRESHOLD_IN_DAYS = 30
ARCHIVE_BATCH_SIZE = 1000

SMALL_ARCHIVE_BATCH_SIZE = 2


@override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=True)
class ArchiveOldRecordsObjectChangeTestCase(TransactionTestCase):
    """
    Test the ArchiveOldRecords system job's handling of ObjectChange records.
    """

    databases = ("default", "job_logs")

    JOB_MODULE = "nautobot.core.jobs.archive"
    JOB_CLASS_NAME = "ArchiveOldRecords"

    def setUp(self):
        super().setUp()

        # The job refuses to run without this, because archiving deletes the records it copies.
        self.add_permissions("extras.delete_objectchange")
        self.add_permissions("extras.add_archivedobjectchange")
        # A forced cascade deletes an object change's metadata too, which the user must be permitted to do.
        self.add_permissions("extras.delete_objectmetadata")

        # Remove any left over models that may exist in order to provide a clean environment
        # for testing
        ObjectChange.objects.all().delete()
        ArchivedObjectChange.objects.all().delete()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def make_object_change(self, *, age_in_days, **kwargs):
        """
        Create an `ObjectChange` whose `time` is `age_in_days` in the past.

        Built field by field rather than through `ObjectChangeFactory`. A factory's output depends on the
        sequence of factory calls made before it, so it shifts with test ordering and with whether the
        fixture cache was used. Several of its fields are also filled only part of the time, which would
        leave the archive comparison tests asserting `None == None` on a given run.

        Every field the archive copies is given a value here, so those comparisons always compare
        something, and two runs of the same test build the same record.
        """
        timestamp = timezone.now() - timedelta(days=age_in_days)
        changed_object_type = ContentType.objects.get_for_model(Status)
        object_change_fields = {
            "user": self.user,
            "user_name": self.user.username,
            "request_id": uuid.uuid4(),
            "action": ObjectChangeActionChoices.ACTION_UPDATE,
            "changed_object_type": changed_object_type,
            "changed_object_id": uuid.uuid4(),
            "change_context": ObjectChangeEventContextChoices.CONTEXT_ORM,
            "change_context_detail": "archive test change",
            "related_object_type": changed_object_type,
            "related_object_id": uuid.uuid4(),
            "object_repr": "archive test object",
            "object_data": {"name": "archive test object"},
            "object_data_v2": {"name": "archive test object"},
        }
        object_change_fields.update(kwargs)

        new_object_change = ObjectChange.objects.create(**object_change_fields)
        # `time` is `auto_now_add`, which overrides whatever the insert supplies, so it is written once
        # the row exists. `auto_now_add` only applies to the insert, so this second save keeps the value.
        new_object_change.time = timestamp
        new_object_change.save()

        # Reloaded so that its `JSONField`s hold what the database holds rather than what was passed in.
        new_object_change.refresh_from_db()
        return new_object_change

    def run_archive_old_records_job(self, **kwargs):
        """
        Run the job against ObjectChange only.

        The threshold and batch size are passed on every run. `run()` has no setting to fall back on,
        so leaving them out hands it `None` rather than a default.
        """
        kwargs.setdefault("selected_models_to_archive", ["extras.ObjectChange"])
        kwargs.setdefault("archive_age_threshold", ARCHIVE_AGE_THRESHOLD_IN_DAYS)
        kwargs.setdefault("archive_batch_size", ARCHIVE_BATCH_SIZE)
        kwargs.setdefault("dryrun", False)

        return create_job_result_and_run_job(
            self.JOB_MODULE, self.JOB_CLASS_NAME, username=self.user.username, **kwargs
        )

    def get_job_log_messages(self, job_result):
        return list(job_result.job_log_entries.values_list("message", flat=True))

    @staticmethod
    def is_handle_deleted_object_connected_to_pre_delete_signal():
        """Whether Nautobot's global change log receiver is currently listening for `pre_delete`."""
        for receiver_entry in pre_delete.receivers:
            receiver = receiver_entry[1]
            resolved_receiver = receiver() if isinstance(receiver, weakref.ReferenceType) else receiver
            if resolved_receiver is _handle_deleted_object:
                return True
        return False

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_dryrun_reports_without_moving_anything(self):
        object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(job_result)
        self.assertTrue(ObjectChange.objects.filter(pk=object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        self.assertTrue(any("Dry Run" in message for message in self.get_job_log_messages(job_result)))

    def test_a_dry_run_counts_only_records_past_the_threshold(self):
        self.make_object_change(age_in_days=90)
        self.make_object_change(age_in_days=1)

        job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(job_result)
        self.assertEqual(job_result.result["extras.ObjectChange"], 1)

    def test_records_older_than_the_threshold_are_archived(self):
        """Records past the threshold move to the archive; records inside it stay live."""
        old_object_change = self.make_object_change(age_in_days=90)
        recent_object_change = self.make_object_change(age_in_days=5)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        # Confirm Old Is Archived
        self.assertFalse(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertTrue(ArchivedObjectChange.objects.filter(pk=old_object_change.pk).exists())
        # Confirm Recent Is Not Archived
        self.assertTrue(ObjectChange.objects.filter(pk=recent_object_change.pk).exists())
        self.assertFalse(ArchivedObjectChange.objects.filter(pk=recent_object_change.pk).exists())

    def test_the_job_returns_a_count_for_every_archivable_model(self):
        """A model the run was not asked to archive reports 0 rather than being absent from the result."""
        self.make_object_change(age_in_days=90)
        self.make_object_change(age_in_days=90)
        self.make_object_change(age_in_days=5)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertEqual(
            job_result.result,
            {
                "extras.ObjectChange": 2,
                "extras.JobResult": 0,
                "extras.JobLogEntry": 0,
                "extras.JobConsoleEntry": 0,
            },
        )

    def test_nothing_is_archived_when_every_record_is_inside_the_threshold(self):
        recent_object_change = self.make_object_change(age_in_days=5)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertTrue(ObjectChange.objects.filter(pk=recent_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        does_no_object_change_record_log_output_exist = any(
            "No ObjectChange records older than" in message for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_no_object_change_record_log_output_exist)

    def test_every_archived_object_change_field_matches_every_object_change_field(self):
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)

        archived_object_change = ArchivedObjectChange.objects.get(pk=old_object_change.pk)
        for field in ArchivedObjectChange._meta.fields:
            with self.subTest(field=field.name):
                archived_object_change_field_value = getattr(archived_object_change, field.name)
                object_change_field_value = getattr(old_object_change, field.name)
                self.assertEqual(archived_object_change_field_value, object_change_field_value)

    def test_archival_runs_in_batches_of_the_requested_size(self):
        # Batching is determined by log output
        for _ in range(5):
            self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(job_result)
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.assertEqual(ArchivedObjectChange.objects.count(), 5)
        batch_messages = [message for message in self.get_job_log_messages(job_result) if message.startswith("Batch ")]
        self.assertEqual(len(batch_messages), 3, batch_messages)

    def test_records_that_share_a_timestamp_are_all_archived(self):
        object_changes = [self.make_object_change(age_in_days=90) for _ in range(5)]
        shared_timestamp = timezone.now() - timedelta(days=90)
        ObjectChange.objects.filter(pk__in=[object_change.pk for object_change in object_changes]).update(
            time=shared_timestamp
        )

        job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(job_result)
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.assertEqual(
            set(ArchivedObjectChange.objects.values_list("pk", flat=True)),
            {object_change.pk for object_change in object_changes},
        )

    def test_batch_iteration_ends_when_the_records_are_not_deleted(self):
        object_changes = [self.make_object_change(age_in_days=90) for _ in range(5)]

        maximum_batch_count = 10

        yielded_pks = []
        for batch_number, record_batch in enumerate(
            _iterate_records_by_timestamp(ObjectChange.objects.all(), "time", SMALL_ARCHIVE_BATCH_SIZE)
        ):
            self.assertLess(batch_number, maximum_batch_count)
            yielded_pks.extend(record.pk for record in record_batch)

        self.assertEqual(len(yielded_pks), len(object_changes))
        self.assertEqual(set(yielded_pks), {object_change.pk for object_change in object_changes})

    def test_a_shared_timestamp_split_across_batches_yields_each_record_exactly_once(self):
        shared_timestamp_record_count = 7
        older_object_change = self.make_object_change(age_in_days=120)
        shared_timestamp_object_changes = [
            self.make_object_change(age_in_days=90) for _ in range(shared_timestamp_record_count)
        ]
        newer_object_change = self.make_object_change(age_in_days=60)

        shared_timestamp = timezone.now() - timedelta(days=90)
        ObjectChange.objects.filter(
            pk__in=[object_change.pk for object_change in shared_timestamp_object_changes]
        ).update(time=shared_timestamp)

        expected_pks = [
            older_object_change.pk,
            *[object_change.pk for object_change in shared_timestamp_object_changes],
            newer_object_change.pk,
        ]
        self.assertGreater(shared_timestamp_record_count, SMALL_ARCHIVE_BATCH_SIZE)
        maximum_batch_count = len(expected_pks) + 1

        batch_sizes = []
        yielded_pks = []
        for batch_number, record_batch in enumerate(
            _iterate_records_by_timestamp(ObjectChange.objects.all(), "time", SMALL_ARCHIVE_BATCH_SIZE)
        ):
            self.assertLess(batch_number, maximum_batch_count)
            batch_sizes.append(len(record_batch))
            yielded_pks.extend(record.pk for record in record_batch)

        self.assertEqual(sorted(yielded_pks), sorted(expected_pks))
        self.assertEqual(batch_sizes, [SMALL_ARCHIVE_BATCH_SIZE] * 4 + [1])

    def test_records_at_or_after_the_threshold_are_not_returned(self):
        for age_in_days in (120, 90, 60, 10, 5):
            self.make_object_change(age_in_days=age_in_days, object_repr=f"object change {age_in_days} days old")
        threshold_timestamp = timezone.now() - timedelta(days=ARCHIVE_AGE_THRESHOLD_IN_DAYS)

        records_before_threshold = ObjectChange.objects.filter(time__lt=threshold_timestamp).order_by("time", "pk")
        expected_records = list(records_before_threshold)
        expected_record_count = 3
        self.assertEqual(len(expected_records), expected_record_count)
        maximum_batch_count = expected_record_count + 1

        records = []
        for batch_number, record_batch in enumerate(
            _iterate_records_by_timestamp(records_before_threshold, "time", SMALL_ARCHIVE_BATCH_SIZE)
        ):
            self.assertLess(batch_number, maximum_batch_count)
            records.extend(record_batch)

        self.assertEqual(records, expected_records)

    def test_rerunning_overwrites_rather_than_duplicating(self):
        """Archiving Object Changes makes the assumption that Object Changes do not change state.
        The job itself will overwrite a record if it already exists out of simplicity.
        """
        old_object_change = self.make_object_change(age_in_days=90)
        self.assertJobResultStatus(self.run_archive_old_records_job())

        # Stand the record back up under the primary key already in the archive, which is the state an
        # interrupted run leaves behind.
        second_round_object_repr = "second round archival"
        self.make_object_change(age_in_days=90, id=old_object_change.pk, object_repr=second_round_object_repr)

        self.assertJobResultStatus(self.run_archive_old_records_job())

        self.assertEqual(ArchivedObjectChange.objects.filter(pk=old_object_change.pk).count(), 1)
        self.assertEqual(
            ArchivedObjectChange.objects.get(pk=old_object_change.pk).object_repr, second_round_object_repr
        )
        self.assertFalse(ObjectChange.objects.filter(pk=old_object_change.pk).exists())

    def test_a_batch_that_fails_also_fails_the_job_and_leaves_the_live_records(self):
        """The live record is deleted only after its copy lands, so a failed batch loses nothing."""
        old_object_change = self.make_object_change(age_in_days=90)
        archive_failure_message = "Archive Unavailable"

        with mock.patch.object(
            ArchiveOldRecords,
            "_process_archive_object_change_batch",
            side_effect=RuntimeError(archive_failure_message),
        ):
            job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        does_archive_failure_message_exist = any(
            archive_failure_message in message for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_archive_failure_message_exist)

    def test_a_batch_that_fails_logs_which_batch_stopped_and_how_much_was_archived(self):
        for _ in range(4):
            self.make_object_change(age_in_days=90)
        archive_failure_message = "Archive Unavailable"
        archived_count_before_failure = 2

        with mock.patch.object(
            ArchiveOldRecords,
            "_process_archive_object_change_batch",
            side_effect=[archived_count_before_failure, RuntimeError(archive_failure_message)],
        ):
            job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        expected_stopping_message = (
            f"Stopping at batch 1: {archive_failure_message}. Archived 2 ObjectChange records before stopping."
        )
        self.assertIn(expected_stopping_message, self.get_job_log_messages(job_result))

    @override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=False)
    def test_forcing_cascade_delete_is_blocked_while_the_setting_is_disabled(self):
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        does_disabled_message_exist = any(
            "ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED" in message
            for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_disabled_message_exist)

    @override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=False)
    def test_a_superuser_is_also_blocked_from_forcing_cascade_delete(self):
        self.user.is_superuser = True
        self.user.save()

        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)

    @override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=False)
    def test_the_job_still_runs_without_forcing_while_the_setting_is_disabled(self):
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertFalse(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 1)

    @override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=False)
    def test_a_forced_dry_run_is_blocked_while_the_setting_is_disabled(self):
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(force_cascade_delete=True, dryrun=True)

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())

    def test_an_ordinary_user_holding_the_granted_permissions_archives_records(self):
        """
        The job has to work for a user who holds the permissions outright rather than by being a superuser.

        `create_job_result_and_run_job` passes `is_superuser` only as a `get_or_create` default, and
        `setUpNautobot` has already created this user, so that default never applies. Asserted here so a
        change to either helper cannot quietly turn every archive test into a superuser run that would
        pass no matter what the permission checks did.
        """
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertEqual(job_result.user.pk, self.user.pk)
        self.assertFalse(job_result.user.is_superuser)
        self.assertFalse(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 1)

    def test_an_ordinary_user_without_the_archive_add_permission_fails_the_job(self):
        """The archived copy is written on the user's behalf, so the run needs their permission to add it."""
        self.remove_permissions("extras.add_archivedobjectchange")
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertFalse(job_result.user.is_superuser)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        does_permission_message_exist = any(
            "does not have permission to add ArchivedObjectChange records" in message
            for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_permission_message_exist)

    def test_a_user_without_delete_permission_fails_the_job(self):
        """`restrict()` alone would archive nothing and still report success, so the job asks outright."""
        self.user.object_permissions.clear()
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        does_permission_message_exist = any(
            "does not have permission to delete ObjectChange records" in message
            for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_permission_message_exist)

    def test_records_deleted_alongside_an_object_change_are_not_a_discrepancy(self):
        """
        `delete()` reports a total across every model it touched, not only the one being archived.

        An ObjectChange takes its ObjectMetadata with it, so a check written against that total would
        report a mismatch on a run where nothing is actually wrong.
        """
        old_object_change = self.make_object_change(age_in_days=90)
        metadata_type = MetadataType.objects.create(
            name="Archive Discrepancy Probe", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        object_change_content_type = ContentType.objects.get_for_model(ObjectChange)
        metadata_type.content_types.set([object_change_content_type])
        ObjectMetadata.objects.create(
            metadata_type=metadata_type,
            assigned_object_type=object_change_content_type,
            assigned_object_id=old_object_change.pk,
            scoped_fields=["change_context_detail"],
            _value="probe",
        )

        job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(job_result)
        self.assertTrue(ArchivedObjectChange.objects.filter(pk=old_object_change.pk).exists())
        # Asserted on the level rather than the wording, so rephrasing the message cannot hide a regression.
        error_messages = list(
            job_result.job_log_entries.filter(log_level=LogLevelChoices.LOG_ERROR).values_list("message", flat=True)
        )
        self.assertEqual(error_messages, [])

    def test_an_object_change_with_metadata_is_held_hot(self):
        old_object_change = self.make_object_change(age_in_days=90)
        metadata_type = MetadataType.objects.create(
            name="Archive Hold Hot Probe", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        object_change_content_type = ContentType.objects.get_for_model(ObjectChange)
        metadata_type.content_types.set([object_change_content_type])
        ObjectMetadata.objects.create(
            metadata_type=metadata_type,
            assigned_object_type=object_change_content_type,
            assigned_object_id=old_object_change.pk,
            scoped_fields=["change_context_detail"],
            _value="probe",
        )

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        self.assertEqual(ObjectMetadata.objects.filter(assigned_object_id=old_object_change.pk).count(), 1)

    def test_object_changes_the_user_cannot_add_to_the_archive_stay_live(self):
        """An `add` constraint on the archived copies is checked against each written copy, record by record."""
        permitted_object_change = self.make_object_change(age_in_days=90, object_repr="permitted object")
        unpermitted_object_change = self.make_object_change(age_in_days=90, object_repr="unpermitted object")
        self.remove_permissions("extras.add_archivedobjectchange")
        self.add_permissions("extras.add_archivedobjectchange", constraints={"object_repr": "permitted object"})

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertTrue(ArchivedObjectChange.objects.filter(pk=permitted_object_change.pk).exists())
        self.assertFalse(ObjectChange.objects.filter(pk=permitted_object_change.pk).exists())
        self.assertFalse(ArchivedObjectChange.objects.filter(pk=unpermitted_object_change.pk).exists())
        self.assertTrue(ObjectChange.objects.filter(pk=unpermitted_object_change.pk).exists())
        self.assertEqual(job_result.result["extras.ObjectChange"], 1)
        self.assertIn(
            f"Not archiving 1 records, because user {self.user} is not permitted to add them to"
            " extras.ArchivedObjectChange.",
            self.get_job_log_messages(job_result),
        )

    def test_object_changes_held_hot_are_reported(self):
        self.make_object_change(age_in_days=90)
        held_object_change = self.make_object_change(age_in_days=90)
        metadata_type = MetadataType.objects.create(
            name="Archive Hold Report Probe", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        object_change_content_type = ContentType.objects.get_for_model(ObjectChange)
        metadata_type.content_types.set([object_change_content_type])
        ObjectMetadata.objects.create(
            metadata_type=metadata_type,
            assigned_object_type=object_change_content_type,
            assigned_object_id=held_object_change.pk,
            scoped_fields=["change_context_detail"],
            _value="probe",
        )

        job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertEqual(ArchivedObjectChange.objects.count(), 1)
        does_omit_message_exist = any(
            "Omitting 1 ObjectChange records" in message for message in self.get_job_log_messages(job_result)
        )
        self.assertTrue(does_omit_message_exist, self.get_job_log_messages(job_result))

    def test_a_falsy_force_value_does_not_release_generic_relations(self):
        old_object_change = self.make_object_change(age_in_days=90)
        metadata_type = MetadataType.objects.create(
            name="Archive Falsy Force Probe", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        object_change_content_type = ContentType.objects.get_for_model(ObjectChange)
        metadata_type.content_types.set([object_change_content_type])
        ObjectMetadata.objects.create(
            metadata_type=metadata_type,
            assigned_object_type=object_change_content_type,
            assigned_object_id=old_object_change.pk,
            scoped_fields=["change_context_detail"],
            _value="probe",
        )

        for falsy_force_value in (False, None, 0, ""):
            remaining_object_changes = exclude_records_whose_relations_block_deletion(
                ObjectChange.objects.all(), ObjectChange, (), falsy_force_value, logging.getLogger(__name__)
            )
            self.assertNotIn(old_object_change, remaining_object_changes, falsy_force_value)

    def test_a_reverse_relation_without_a_related_name_is_queried_by_its_query_name(self):
        """
        `get_accessor_name()` yields `<model>_set` for a reverse foreign key that declares no
        `related_name`, which is not a name the ORM will resolve in a lookup. The query name is, so an
        app model pointing at an archived model without a `related_name` must not break the filter.

        `ContentType` is used because core models all declare a `related_name`; it carries several
        reverse foreign keys that do not.
        """
        content_type_relations = [
            related_object
            for related_object in ContentType._meta.related_objects
            if isinstance(related_object, ManyToOneRel)
            and related_object.get_accessor_name() != related_object.field.related_query_name()
        ]
        self.assertNotEqual(content_type_relations, [], "ContentType no longer has a relation without a related_name")

        remaining_content_types = exclude_records_whose_relations_block_deletion(
            ContentType.objects.all(), ContentType, (), False, logging.getLogger(__name__)
        )
        # Evaluating the queryset is what raises FieldError when the accessor name is used as a lookup.
        self.assertGreaterEqual(remaining_content_types.count(), 0)

    def test_protecting_relations_hold_records_hot_even_when_forced(self):
        protected_manufacturer = Manufacturer.objects.create(name="Archive Protected Probe")
        DeviceType.objects.create(manufacturer=protected_manufacturer, model="Archive Probe Model")
        unprotected_manufacturer = Manufacturer.objects.create(name="Archive Unprotected Probe")

        remaining_manufacturers = exclude_records_whose_relations_block_deletion(
            Manufacturer.objects.all(),
            Manufacturer,
            (),
            force_cascade_delete=True,
            logger=logging.getLogger(__name__),
        )

        self.assertNotIn(protected_manufacturer, remaining_manufacturers)
        self.assertIn(unprotected_manufacturer, remaining_manufacturers)

    def test_a_model_this_job_does_not_archive_fails_the_job(self):
        """
        An unrecognised name matches none of the `in selected_models` checks, so without the guard the
        run would archive nothing and report success.

        The lowercase spelling is used deliberately: it is what this job accepted before the labels were
        taken from `_meta.label`, so it is the mistake most likely to reach it.
        """
        old_object_change = self.make_object_change(age_in_days=90)

        job_result = self.run_archive_old_records_job(selected_models_to_archive=["extras.objectchange"])

        self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(ObjectChange.objects.filter(pk=old_object_change.pk).exists())
        self.assertEqual(ArchivedObjectChange.objects.count(), 0)
        # The message names the offending value and what it could have been.
        self.assertIn("extras.objectchange", job_result.traceback)
        self.assertIn("extras.ObjectChange", job_result.traceback)

    def test_handle_deleted_object_is_disconnected_for_pre_delete_signal_during_job_run(self):
        """
        `_handle_deleted_object` is globally connected to the pre_delete signal. Make sure that
        it is disabled when running the `ArchiveOldRecords` job.
        """
        self.make_object_change(age_in_days=90)
        was_handle_deleted_object_connected_during_archival = []

        def record_whether_receiver_is_connected(*args, **kwargs):
            was_handle_deleted_object_connected_during_archival.append(
                self.is_handle_deleted_object_connected_to_pre_delete_signal()
            )
            return {"extras.ObjectChange": 0}

        self.assertTrue(self.is_handle_deleted_object_connected_to_pre_delete_signal())

        with mock.patch.object(
            ArchiveOldRecords,
            "_archive_object_changes",
            side_effect=record_whether_receiver_is_connected,
        ):
            job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(job_result)
        self.assertEqual(was_handle_deleted_object_connected_during_archival, [False])
        self.assertTrue(self.is_handle_deleted_object_connected_to_pre_delete_signal())


@override_config(ARCHIVE_OLD_RECORDS_JOB_FORCE_CASCADE_DELETE_ENABLED=True)
class ArchiveOldRecordsJobResultTestCase(TransactionTestCase):
    """
    Test the ArchiveOldRecords system job's handling of JobResult records and their child records.

    The signal disconnect is deliberately not retested here. It is set up once in `run()` for the whole
    job rather than per model, and `ArchiveOldRecordsObjectChangeTestCase` already covers it.
    """

    databases = ("default", "job_logs")

    JOB_MODULE = "nautobot.core.jobs.archive"
    JOB_CLASS_NAME = "ArchiveOldRecords"

    def setUp(self):
        super().setUp()

        # The job refuses to run without the delete and add permissions, because archiving deletes the records it
        # copies. A job result is also skipped unless the user may delete all of its child entries.
        self.add_permissions("extras.delete_jobresult")
        self.add_permissions("extras.delete_joblogentry")
        self.add_permissions("extras.delete_jobconsoleentry")
        # A forced cascade deletes a job result's metadata and files too, which the user must be permitted to do.
        self.add_permissions("extras.delete_objectmetadata", "extras.delete_fileproxy")
        self.add_permissions("extras.add_archivedjobresult")
        self.add_permissions("extras.add_archivedjoblogentry")
        self.add_permissions("extras.add_archivedjobconsoleentry")

        # Remove any left over models that may exist in order to provide a clean environment
        # for testing. Deleting the parents takes their log and console entries with them.
        JobResult.objects.all().delete()
        ArchivedJobResult.objects.all().delete()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def make_job_result(
        self,
        *,
        age_in_days,
        log_entry_count=0,
        console_entry_count=0,
        status=JobResultStatusChoices.STATUS_SUCCESS,
        **kwargs,
    ):
        """
        Create a `JobResult` that finished `age_in_days` in the past, with the requested child records.

        Built field by field rather than through `JobResultFactory`, for the reasons given on
        `ArchiveOldRecordsObjectChangeTestCase.make_object_change`: factory output depends on the calls
        that preceded it, and it assigns a user only most of the time.

        Eligibility is decided by `date_done`, so the test owns all three timestamps.
        """
        finished_timestamp = timezone.now() - timedelta(days=age_in_days)

        job_result_fields = {
            "name": "Archive Test Job",
            "task_name": "nautobot.core.tests.test_jobs.archive_test_job",
            "user": self.user,
            "status": status,
            "worker": "celery@archive-test",
            "task_args": ["archive test arg"],
            "task_kwargs": {"archive_test_kwarg": "value"},
            "celery_kwargs": {"queue": "default"},
            "result": {"archive_test_result": "value"},
            "traceback": "archive test traceback",
            "meta": {"archive_test_meta": "value"},
        }
        job_result_fields.update(kwargs)

        new_job_result = JobResult.objects.create(**job_result_fields)
        # `date_created` is `auto_now_add`, so all three timestamps are written after the insert.
        new_job_result.date_created = finished_timestamp
        new_job_result.date_started = finished_timestamp
        new_job_result.date_done = finished_timestamp
        new_job_result.save()

        for log_entry_index in range(log_entry_count):
            JobLogEntry.objects.create(
                job_result=new_job_result,
                log_level=LogLevelChoices.LOG_INFO,
                grouping="main",
                message=f"{new_job_result.name} log entry {log_entry_index}",
            )

        for console_entry_index in range(console_entry_count):
            JobConsoleEntry.objects.create(
                job_result=new_job_result,
                text=f"{new_job_result.name} console entry {console_entry_index}",
            )

        new_job_result.refresh_from_db()
        return new_job_result

    def run_archive_old_records_job(self, **kwargs):
        """
        Run the job against JobResult only.

        The threshold and batch size are passed on every run. `run()` has no setting to fall back on,
        so leaving them out hands it `None` rather than a default.
        """
        kwargs.setdefault("selected_models_to_archive", ["extras.JobResult"])
        kwargs.setdefault("archive_age_threshold", ARCHIVE_AGE_THRESHOLD_IN_DAYS)
        kwargs.setdefault("archive_batch_size", ARCHIVE_BATCH_SIZE)
        kwargs.setdefault("dryrun", False)

        return create_job_result_and_run_job(
            self.JOB_MODULE, self.JOB_CLASS_NAME, username=self.user.username, **kwargs
        )

    def get_job_log_messages(self, job_result):
        return list(job_result.job_log_entries.values_list("message", flat=True))

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_dryrun_reports_without_moving_anything(self):
        job_result = self.make_job_result(age_in_days=90, log_entry_count=2, console_entry_count=2)

        archive_job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=job_result.pk).exists())
        self.assertEqual(ArchivedJobResult.objects.count(), 0)
        self.assertEqual(ArchivedJobLogEntry.objects.count(), 0)
        self.assertEqual(ArchivedJobConsoleEntry.objects.count(), 0)
        self.assertTrue(any("Dry Run" in message for message in self.get_job_log_messages(archive_job_result)))

    def test_a_dry_run_counts_only_job_results_past_the_threshold(self):
        self.make_job_result(age_in_days=90, log_entry_count=2, console_entry_count=2)
        self.make_job_result(age_in_days=1, log_entry_count=3, console_entry_count=3)

        archive_job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(
            archive_job_result.result,
            {
                "extras.ObjectChange": 0,
                "extras.JobResult": 1,
                "extras.JobLogEntry": 2,
                "extras.JobConsoleEntry": 2,
            },
        )

    def test_job_results_older_than_the_threshold_are_archived(self):
        """Job results past the threshold move to the archive; job results inside it stay live."""
        old_job_result = self.make_job_result(age_in_days=90)
        recent_job_result = self.make_job_result(age_in_days=5)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        # Confirm Old Is Archived
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertTrue(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        # Confirm Recent Is Not Archived
        self.assertTrue(JobResult.objects.filter(pk=recent_job_result.pk).exists())
        self.assertFalse(ArchivedJobResult.objects.filter(pk=recent_job_result.pk).exists())

    def test_nothing_is_archived_when_every_job_result_is_inside_the_threshold(self):
        recent_job_result = self.make_job_result(age_in_days=5)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=recent_job_result.pk).exists())
        self.assertEqual(ArchivedJobResult.objects.count(), 0)
        does_no_job_result_record_log_output_exist = any(
            "No JobResult records older than" in message for message in self.get_job_log_messages(archive_job_result)
        )
        self.assertTrue(does_no_job_result_record_log_output_exist)

    def test_log_and_console_entries_move_with_their_job_result(self):
        """The children are copied before the live parent is deleted, so the cascade takes only live rows."""
        log_entry_count = 3
        console_entry_count = 2
        old_job_result = self.make_job_result(
            age_in_days=90,
            log_entry_count=log_entry_count,
            console_entry_count=console_entry_count,
        )

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        # Confirm The Children Reached The Archive
        self.assertEqual(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), log_entry_count)
        self.assertEqual(
            ArchivedJobConsoleEntry.objects.filter(job_result_id=old_job_result.pk).count(), console_entry_count
        )
        # Confirm The Live Children Were Cascaded Away With Their Parent
        self.assertFalse(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).exists())
        self.assertFalse(JobConsoleEntry.objects.filter(job_result_id=old_job_result.pk).exists())

    def test_the_job_counts_child_entries_under_their_own_model_labels(self):
        """The children are reported separately from their parent rather than folded into its count."""
        log_entry_count = 3
        console_entry_count = 2
        self.make_job_result(age_in_days=90, log_entry_count=log_entry_count, console_entry_count=console_entry_count)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(
            archive_job_result.result,
            {
                "extras.ObjectChange": 0,
                "extras.JobResult": 1,
                "extras.JobLogEntry": log_entry_count,
                "extras.JobConsoleEntry": console_entry_count,
            },
        )

    def test_a_dry_run_counts_the_children_it_would_archive(self):
        """A dry run reports the same models a real run moves, so the children are counted rather than zeroed."""
        log_entry_count = 3
        console_entry_count = 2
        old_job_result = self.make_job_result(
            age_in_days=90, log_entry_count=log_entry_count, console_entry_count=console_entry_count
        )

        archive_job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(
            archive_job_result.result,
            {
                "extras.ObjectChange": 0,
                "extras.JobResult": 1,
                "extras.JobLogEntry": log_entry_count,
                "extras.JobConsoleEntry": console_entry_count,
            },
        )
        # Counted, but left where they were.
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(ArchivedJobResult.objects.count(), 0)

    def test_child_entries_are_archived_in_chunks_when_they_outnumber_the_batch_size(self):
        """
        A single job result can carry far more children than the parent batch size, so the children are
        chunked independently.

        The counts straddle the chunk boundary on purpose. Four log entries at a chunk size of two divide
        evenly, so the last chunk read comes back empty; five console entries do not, so the last chunk is
        a partial one. Both have to land in full.
        """
        log_entry_count = 4
        console_entry_count = 5
        old_job_result = self.make_job_result(
            age_in_days=90,
            log_entry_count=log_entry_count,
            console_entry_count=console_entry_count,
        )

        archive_job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), log_entry_count)
        self.assertEqual(
            ArchivedJobConsoleEntry.objects.filter(job_result_id=old_job_result.pk).count(), console_entry_count
        )

    def test_an_interrupted_child_archival_resumes_from_where_it_stopped(self):
        """
        Each chunk of children is copied and deleted in one committed transaction, which is what lets a
        failed run be picked up rather than repeated.

        The failure is injected into the third chunk, so two chunks have already committed when it
        raises. What the second run must not do is work through those two again, and what neither run
        may do is lose a record in between: every entry is either archived or still live at all times.
        """
        log_entry_count = 10
        failing_chunk_number = 3
        committed_chunk_count = failing_chunk_number - 1
        archive_failure_message = "Archive Unavailable"

        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=log_entry_count)

        attempted_chunk_count = 0
        unpatched_bulk_create = ArchivedJobLogEntry.objects.bulk_create

        def fail_on_the_third_chunk(*args, **kwargs):
            nonlocal attempted_chunk_count
            attempted_chunk_count += 1
            if attempted_chunk_count == failing_chunk_number:
                raise RuntimeError(archive_failure_message)
            return unpatched_bulk_create(*args, **kwargs)

        with mock.patch.object(ArchivedJobLogEntry.objects, "bulk_create", side_effect=fail_on_the_third_chunk):
            interrupted_job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(interrupted_job_result, JobResultStatusChoices.STATUS_FAILURE)

        archived_before_the_failure = ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count()
        still_live_after_the_failure = JobLogEntry.objects.filter(job_result_id=old_job_result.pk).count()
        # The chunks that committed are in the archive and gone from the live table; the rest are untouched.
        self.assertEqual(archived_before_the_failure, committed_chunk_count * SMALL_ARCHIVE_BATCH_SIZE)
        self.assertEqual(archived_before_the_failure + still_live_after_the_failure, log_entry_count)
        # The parent survives, so its remaining children are still reachable on the next run.
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())

        resumed_job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(resumed_job_result)
        self.assertEqual(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), log_entry_count)
        self.assertFalse(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).exists())
        # The count the second run reports is the remainder, not the whole job result over again.
        expected_resumed_message = f"Archived 1 job results with {still_live_after_the_failure} log entries"
        resumed_job_log_messages = self.get_job_log_messages(resumed_job_result)
        self.assertTrue(
            any(expected_resumed_message in message for message in resumed_job_log_messages),
            resumed_job_log_messages,
        )

    def test_every_archived_job_result_field_matches_every_job_result_field(self):
        """
        `user_name` is excluded because it has no live counterpart; it is covered by its own test.

        Fields are read by `attname` rather than `name` so that the archive's bare id columns line up with
        the live record's foreign keys. `ArchivedJobResult.user_id` is a plain UUID column while
        `JobResult.user` is a relation, and only `attname` names both of them `user_id`.
        """
        old_job_result = self.make_job_result(age_in_days=90)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)

        archived_job_result = ArchivedJobResult.objects.get(pk=old_job_result.pk)
        for field in ArchivedJobResult._meta.fields:
            if field.name == "user_name":
                continue
            with self.subTest(field=field.name):
                archived_job_result_field_value = getattr(archived_job_result, field.attname)
                job_result_field_value = getattr(old_job_result, field.attname)
                self.assertEqual(archived_job_result_field_value, job_result_field_value)

    def test_archived_user_name_is_denormalized_from_the_live_user(self):
        """The archive cannot follow a foreign key into the live user table, so the username is copied."""
        old_job_result = self.make_job_result(age_in_days=90, user=self.user)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        archived_job_result = ArchivedJobResult.objects.get(pk=old_job_result.pk)
        self.assertEqual(archived_job_result.user_name, self.user.username)

    def test_every_archived_child_entry_field_matches_its_live_entry(self):
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=1, console_entry_count=1)
        job_log_entry = JobLogEntry.objects.get(job_result_id=old_job_result.pk)
        job_console_entry = JobConsoleEntry.objects.get(job_result_id=old_job_result.pk)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)

        archived_child_entries_by_live_entry = {
            job_log_entry: ArchivedJobLogEntry.objects.get(pk=job_log_entry.pk),
            job_console_entry: ArchivedJobConsoleEntry.objects.get(pk=job_console_entry.pk),
        }
        for live_entry, archived_entry in archived_child_entries_by_live_entry.items():
            for field in type(archived_entry)._meta.fields:
                with self.subTest(model=type(archived_entry).__name__, field=field.name):
                    self.assertEqual(getattr(archived_entry, field.attname), getattr(live_entry, field.attname))

    def test_a_user_without_delete_permission_fails_the_job(self):
        """`restrict()` alone would archive nothing and still report success, so the job asks outright."""
        self.user.object_permissions.clear()
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=2, console_entry_count=2)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(ArchivedJobResult.objects.count(), 0)
        # The children are still live too, because nothing was deleted.
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), 2)
        does_permission_message_exist = any(
            "does not have permission to delete JobResult records" in message
            for message in self.get_job_log_messages(archive_job_result)
        )
        self.assertTrue(does_permission_message_exist)

    def test_records_deleted_alongside_a_job_result_are_not_a_discrepancy(self):
        """
        `delete()` reports a total across every model it touched, not only the one being archived.

        A job result takes its ObjectMetadata with it, so a check written against that total would
        report a mismatch on a run where nothing is actually wrong.
        """
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=2, console_entry_count=2)
        metadata_type = MetadataType.objects.create(
            name="Archive Discrepancy Probe", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        job_result_content_type = ContentType.objects.get_for_model(JobResult)
        metadata_type.content_types.set([job_result_content_type])
        ObjectMetadata.objects.create(
            metadata_type=metadata_type,
            assigned_object_type=job_result_content_type,
            assigned_object_id=old_job_result.pk,
            scoped_fields=["name"],
            _value="probe",
        )

        archive_job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        # Asserted on the level rather than the wording, so rephrasing the message cannot hide a regression.
        error_messages = list(
            archive_job_result.job_log_entries.filter(log_level=LogLevelChoices.LOG_ERROR).values_list(
                "message", flat=True
            )
        )
        self.assertEqual(error_messages, [])

    def test_a_user_without_child_delete_permission_fails_the_job(self):
        """
        The entries are restricted, and deleting their job result cascades them away regardless.

        Without this gate a user holding only `delete_jobresult` would see no entries to archive, and
        the parent delete would then destroy them with no archived copy. Nothing may move.
        """
        self.user.object_permissions.clear()
        self.add_permissions("extras.delete_jobresult")
        self.add_permissions("extras.add_archivedjobresult")
        log_entry_count = 3
        console_entry_count = 2
        old_job_result = self.make_job_result(
            age_in_days=90, log_entry_count=log_entry_count, console_entry_count=console_entry_count
        )

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result, JobResultStatusChoices.STATUS_FAILURE)
        # Every record is still live, and none of them reached the archive.
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), log_entry_count)
        self.assertEqual(JobConsoleEntry.objects.filter(job_result_id=old_job_result.pk).count(), console_entry_count)
        self.assertEqual(ArchivedJobResult.objects.count(), 0)
        self.assertEqual(ArchivedJobLogEntry.objects.count(), 0)
        self.assertEqual(ArchivedJobConsoleEntry.objects.count(), 0)
        does_permission_message_exist = any(
            "does not have permission to delete Job" in message
            for message in self.get_job_log_messages(archive_job_result)
        )
        self.assertTrue(does_permission_message_exist)

    def test_entries_the_user_cannot_add_to_the_archive_stay_live_with_their_job_result(self):
        """
        An `add` constraint on the archived log entries is checked against each written copy.

        The permitted entry is copied to the archive and deleted. The other entry stays in the live table, and so does
        the job result, so that the remaining entry is not deleted with it. A later run without the constraint
        archives the remaining entry and the job result.
        """
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
        permitted_message = f"{old_job_result.name} log entry 0"
        self.remove_permissions("extras.add_archivedjoblogentry")
        self.add_permissions("extras.add_archivedjoblogentry", constraints={"message": permitted_message})

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertTrue(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(
            list(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).values_list("message", flat=True)),
            [permitted_message],
        )
        self.assertEqual(
            list(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).values_list("message", flat=True)),
            [f"{old_job_result.name} log entry 1"],
        )
        job_log_messages = self.get_job_log_messages(archive_job_result)
        self.assertIn(
            f"Not archiving 1 records, because user {self.user} is not permitted to add them to"
            " extras.ArchivedJobLogEntry.",
            job_log_messages,
        )
        self.assertTrue(any(message.startswith("Not deleting 1 JobResult records") for message in job_log_messages))

        self.remove_permissions("extras.add_archivedjoblogentry", constraints={"message": permitted_message})
        self.add_permissions("extras.add_archivedjoblogentry")

        resumed_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(resumed_job_result)
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), 2)

    def test_a_job_result_with_entries_the_user_cannot_delete_is_not_archived(self):
        """
        Deleting the job result would delete entries that the user is not permitted to delete.

        The user may not delete only one of the skipped job result's two entries, but the whole job result must still
        be skipped.
        """
        for child_model, related_name in ((JobLogEntry, "job_log_entries"), (JobConsoleEntry, "job_console_entries")):
            child_entry_count_kwarg = "log_entry_count" if child_model is JobLogEntry else "console_entry_count"
            with self.subTest(child_model=child_model._meta.label):
                held_job_result = self.make_job_result(age_in_days=90, **{child_entry_count_kwarg: 2})
                permitted_job_result = self.make_job_result(age_in_days=90, **{child_entry_count_kwarg: 1})
                permitted_entry_pks = [
                    str(getattr(held_job_result, related_name).order_by("pk").first().pk),
                    str(getattr(permitted_job_result, related_name).get().pk),
                ]
                permission_name = f"extras.delete_{child_model._meta.model_name}"
                self.remove_permissions(permission_name)
                self.add_permissions(permission_name, constraints={"pk__in": permitted_entry_pks})

                archive_job_result = self.run_archive_old_records_job()

                self.assertJobResultStatus(archive_job_result)
                self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertEqual(child_model.objects.filter(job_result_id=held_job_result.pk).count(), 2)
                self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertTrue(ArchivedJobResult.objects.filter(pk=permitted_job_result.pk).exists())
                self.assertIn(
                    f"Skipping 1 JobResult records whose deletion would also delete the {child_model._meta.label}"
                    f" records that reference them through {child_model._meta.label}.job_result. User {self.user} is"
                    f" not permitted to delete those {child_model._meta.label} records.",
                    self.get_job_log_messages(archive_job_result),
                )

                self.remove_permissions(permission_name, constraints={"pk__in": permitted_entry_pks})
                self.add_permissions(permission_name)
                held_job_result.delete()

    def test_a_job_result_the_user_cannot_add_to_the_archive_stays_live_with_its_entries(self):
        """
        An `add` constraint on the archived job results is checked against each written copy.

        The entries of a job result whose copy is not permitted are not archived either, so no part of that job result
        is copied to the archive.
        """
        permitted_job_result = self.make_job_result(age_in_days=90, log_entry_count=1, name="Permitted Archive Job")
        unpermitted_job_result = self.make_job_result(age_in_days=90, log_entry_count=1, name="Unpermitted Archive Job")
        self.remove_permissions("extras.add_archivedjobresult")
        self.add_permissions("extras.add_archivedjobresult", constraints={"name": "Permitted Archive Job"})

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertFalse(JobResult.objects.filter(pk=permitted_job_result.pk).exists())
        self.assertTrue(ArchivedJobResult.objects.filter(pk=permitted_job_result.pk).exists())
        self.assertTrue(JobResult.objects.filter(pk=unpermitted_job_result.pk).exists())
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=unpermitted_job_result.pk).count(), 1)
        self.assertFalse(ArchivedJobResult.objects.filter(pk=unpermitted_job_result.pk).exists())
        self.assertFalse(ArchivedJobLogEntry.objects.filter(job_result_id=unpermitted_job_result.pk).exists())
        self.assertEqual(archive_job_result.result["extras.JobResult"], 1)
        self.assertIn(
            f"Not archiving 1 records, because user {self.user} is not permitted to add them to"
            " extras.ArchivedJobResult.",
            self.get_job_log_messages(archive_job_result),
        )

    def test_job_results_that_have_not_finished_are_not_archived(self):
        """
        A job that is still going has no end time, so a long running one would otherwise be deleted out
        from under the task that is writing to it. The status check states that requirement a second way.
        """
        unfinished_job_result = self.make_job_result(age_in_days=90, status=JobResultStatusChoices.STATUS_STARTED)

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=unfinished_job_result.pk).exists())
        self.assertFalse(ArchivedJobResult.objects.filter(pk=unfinished_job_result.pk).exists())

    def test_job_results_that_carry_files_are_not_archived(self):
        """
        A `FileProxy` is a third cascade child with no archived counterpart, and deleting its job result
        destroys the stored file along with the row. Those job results are left alone rather than archived
        with their files silently discarded.
        """
        old_job_result = self.make_job_result(age_in_days=90)
        file_proxy = FileProxy.objects.create(
            name="output.txt",
            file=ContentFile(b"job output", name="output.txt"),
            job_result=old_job_result,
        )

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertFalse(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertTrue(FileProxy.objects.filter(pk=file_proxy.pk).exists())

    def test_a_job_result_that_carries_files_is_archived_when_forced(self):
        old_job_result = self.make_job_result(age_in_days=90)
        forced_file_proxy = FileProxy.objects.create(
            name="forced-output.txt",
            file=ContentFile(b"job output", name="forced-output.txt"),
            job_result=old_job_result,
        )

        archive_job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertFalse(FileProxy.objects.filter(pk=forced_file_proxy.pk).exists())

    def test_job_results_held_hot_are_reported(self):
        self.make_job_result(age_in_days=90)
        held_job_result = self.make_job_result(age_in_days=90)
        FileProxy.objects.create(
            name="held-report-probe.txt",
            file=ContentFile(b"job output", name="held-report-probe.txt"),
            job_result=held_job_result,
        )

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(ArchivedJobResult.objects.count(), 1)
        does_omit_message_exist = any(
            "Omitting 1 JobResult records" in message for message in self.get_job_log_messages(archive_job_result)
        )
        self.assertTrue(does_omit_message_exist, self.get_job_log_messages(archive_job_result))

    def test_a_falsy_force_value_does_not_release_cascading_relations(self):
        old_job_result = self.make_job_result(age_in_days=90)
        FileProxy.objects.create(
            name="falsy-force-probe.txt",
            file=ContentFile(b"job output", name="falsy-force-probe.txt"),
            job_result=old_job_result,
        )

        for falsy_force_value in (False, None, 0, ""):
            remaining_job_results = exclude_records_whose_relations_block_deletion(
                JobResult.objects.all(),
                JobResult,
                (JobLogEntry, JobConsoleEntry),
                falsy_force_value,
                logging.getLogger(__name__),
            )
            self.assertNotIn(old_job_result, remaining_job_results, falsy_force_value)

    def test_archival_runs_in_batches_of_the_requested_size(self):
        # Batching is determined by log output
        job_result_count = 5
        for _ in range(job_result_count):
            self.make_job_result(age_in_days=90)

        archive_job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(ArchivedJobResult.objects.count(), job_result_count)
        batch_messages = [
            message for message in self.get_job_log_messages(archive_job_result) if message.startswith("Batch ")
        ]
        self.assertEqual(len(batch_messages), 3, batch_messages)

    def test_rerunning_overwrites_rather_than_duplicating(self):
        """Archiving job results assumes a finished job result no longer changes state.

        The job itself will overwrite a record if it already exists out of simplicity.
        """
        old_job_result = self.make_job_result(age_in_days=90)
        self.assertJobResultStatus(self.run_archive_old_records_job())

        # Stand the record back up under the primary key already in the archive, which is the state an
        # interrupted run leaves behind.
        second_round_name = "second round archival"
        self.make_job_result(age_in_days=90, id=old_job_result.pk, name=second_round_name)

        self.assertJobResultStatus(self.run_archive_old_records_job())

        self.assertEqual(ArchivedJobResult.objects.filter(pk=old_job_result.pk).count(), 1)
        self.assertEqual(ArchivedJobResult.objects.get(pk=old_job_result.pk).name, second_round_name)
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())

    def test_a_batch_that_fails_also_fails_the_job_and_leaves_the_live_records(self):
        """The live record is deleted only after its copy lands, so a failed batch loses nothing."""
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=2, console_entry_count=2)
        archive_failure_message = "Archive Unavailable"

        with mock.patch.object(
            ArchiveOldRecords,
            "_process_archive_job_result_batch",
            side_effect=RuntimeError(archive_failure_message),
        ):
            archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result, JobResultStatusChoices.STATUS_FAILURE)
        self.assertTrue(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), 2)
        self.assertEqual(JobConsoleEntry.objects.filter(job_result_id=old_job_result.pk).count(), 2)
        self.assertEqual(ArchivedJobResult.objects.count(), 0)
        does_archive_failure_message_exist = any(
            archive_failure_message in message for message in self.get_job_log_messages(archive_job_result)
        )
        self.assertTrue(does_archive_failure_message_exist)

    def test_a_batch_that_fails_logs_which_batch_stopped_and_how_much_was_archived(self):
        for _ in range(4):
            self.make_job_result(age_in_days=90)
        archive_failure_message = "Archive Unavailable"
        archived_count_before_failure = 2
        archived_counts_before_failure = {
            "extras.JobResult": archived_count_before_failure,
            "extras.JobLogEntry": 0,
            "extras.JobConsoleEntry": 0,
        }

        with mock.patch.object(
            ArchiveOldRecords,
            "_process_archive_job_result_batch",
            side_effect=[archived_counts_before_failure, RuntimeError(archive_failure_message)],
        ):
            archive_job_result = self.run_archive_old_records_job(archive_batch_size=SMALL_ARCHIVE_BATCH_SIZE)

        expected_stopping_message = (
            f"Stopping at batch 1: {archive_failure_message}. Archived 2 JobResult records before stopping."
        )
        self.assertIn(expected_stopping_message, self.get_job_log_messages(archive_job_result))

    # The example_app models below are imported inside each test because example_app is an optional app: the
    # module must still import when it is not installed, and the `example_app` tag skips these tests then.
    @tag("example_app")
    def test_a_job_result_whose_log_entry_is_protected_is_not_archived_even_when_forced(self):
        """
        Deleting the job result would cascade to the log entry, which a `RESTRICT` reference forbids.

        Only one of the two log entries is referenced. A filter that tests each log entry separately would select the
        job result for archival, because the other log entry is not referenced.
        """
        from example_app.models import AnotherExampleModel

        for force_cascade_delete in (False, True):
            with self.subTest(force_cascade_delete=force_cascade_delete):
                held_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
                protecting_record = AnotherExampleModel.objects.create(
                    name=f"Archive Protect Probe {force_cascade_delete}",
                    job_log_entry=held_job_result.job_log_entries.first(),
                )
                free_job_result = self.make_job_result(age_in_days=90, log_entry_count=1)

                archive_job_result = self.run_archive_old_records_job(force_cascade_delete=force_cascade_delete)

                self.assertJobResultStatus(archive_job_result)
                self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertEqual(JobLogEntry.objects.filter(job_result_id=held_job_result.pk).count(), 2)
                self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertFalse(ArchivedJobLogEntry.objects.filter(job_result_id=held_job_result.pk).exists())
                self.assertTrue(ArchivedJobResult.objects.filter(pk=free_job_result.pk).exists())
                self.assertTrue(
                    any(
                        message.startswith("Omitting 1 JobResult records")
                        for message in self.get_job_log_messages(archive_job_result)
                    )
                )

                protecting_record.delete()

    @tag("example_app")
    def test_a_job_result_whose_log_entry_would_cascade_is_not_archived(self):
        """
        Deleting the job result would cascade through the log entry to a record that is not archived.

        The log entry must not be lost either. It must stay in the live table with its job result, rather than be
        skipped when the child entries are archived and then deleted with the job result.
        """
        from example_app.models import ExampleModel

        held_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
        cascading_record = ExampleModel.objects.create(
            name="Archive Cascade Probe", job_log_entry=held_job_result.job_log_entries.first()
        )

        archive_job_result = self.run_archive_old_records_job()

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=held_job_result.pk).count(), 2)
        self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertTrue(ExampleModel.objects.filter(pk=cascading_record.pk).exists())
        self.assertIn(FORCE_CASCADE_DELETE_HINT, self.get_job_log_messages(archive_job_result))

    @tag("example_app")
    def test_a_job_result_whose_log_entry_would_cascade_is_archived_when_forced(self):
        """
        Deleting the cascaded record also deletes its many-to-many links in both directions.

        The record at the other end of those links is not deleted.
        """
        from example_app.models import ExampleModel

        self.add_permissions("example_app.delete_examplemodel")
        old_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
        cascading_record = ExampleModel.objects.create(
            name="Archive Forced Cascade Probe", job_log_entry=old_job_result.job_log_entries.first()
        )
        linked_record = ExampleModel.objects.create(name="Archive Forced Cascade Linked Probe")
        cascading_record.linked_example_models.add(linked_record)
        linked_record.linked_example_models.add(cascading_record)

        archive_job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertFalse(JobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertTrue(ArchivedJobResult.objects.filter(pk=old_job_result.pk).exists())
        self.assertEqual(ArchivedJobLogEntry.objects.filter(job_result_id=old_job_result.pk).count(), 2)
        self.assertFalse(ExampleModel.objects.filter(pk=cascading_record.pk).exists())
        self.assertTrue(ExampleModel.objects.filter(pk=linked_record.pk).exists())
        self.assertFalse(linked_record.linked_example_models.exists())
        self.assertFalse(linked_record.linking_example_models.exists())

    @tag("example_app")
    def test_a_forced_cascade_into_a_record_the_user_cannot_delete_holds_the_job_result(self):
        """Forcing accepts the cascade, but not the deletion of a record the user is not permitted to delete."""
        from example_app.models import ExampleModel

        held_job_result = self.make_job_result(age_in_days=90, log_entry_count=1)
        cascading_record = ExampleModel.objects.create(
            name="Archive Unpermitted Cascade Probe", job_log_entry=held_job_result.job_log_entries.first()
        )

        archive_job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertTrue(ExampleModel.objects.filter(pk=cascading_record.pk).exists())
        self.assertIn(
            "Skipping 1 JobResult records whose deletion would also delete the example_app.ExampleModel records that"
            " reference them through example_app.ExampleModel.job_log_entry -> extras.JobLogEntry.job_result. User"
            f" {self.user} is not permitted to delete those example_app.ExampleModel records.",
            self.get_job_log_messages(archive_job_result),
        )

    @tag("example_app")
    def test_a_protected_record_beyond_a_forced_cascade_holds_the_job_result(self):
        """
        Forcing allows the cascade to delete the `ExampleModel` record.

        A `PROTECT` reference to that record still prevents its deletion, so the job result is skipped.
        """
        from example_app.models import AnotherExampleModel, ExampleModel

        held_job_result = self.make_job_result(age_in_days=90, log_entry_count=1)
        cascading_record = ExampleModel.objects.create(
            name="Archive Nested Protect Probe", job_log_entry=held_job_result.job_log_entries.first()
        )
        AnotherExampleModel.objects.create(name="Archive Nested Protect Probe", example_model=cascading_record)

        archive_job_result = self.run_archive_old_records_job(force_cascade_delete=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertEqual(JobLogEntry.objects.filter(job_result_id=held_job_result.pk).count(), 1)
        self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
        self.assertTrue(ExampleModel.objects.filter(pk=cascading_record.pk).exists())

    @tag("example_app")
    def test_a_job_result_whose_log_entry_is_referenced_without_a_reverse_relation_is_not_archived(self):
        """
        `AnotherExampleModel.job_log_entry_without_reverse_relation` cascades, but no lookup path can include it.

        The record it would delete cannot be checked, so the job result is skipped even when the cascade is forced.
        """
        from example_app.models import AnotherExampleModel

        for force_cascade_delete in (False, True):
            with self.subTest(force_cascade_delete=force_cascade_delete):
                held_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
                referencing_record = AnotherExampleModel.objects.create(
                    name=f"Archive Hidden Relation Probe {force_cascade_delete}",
                    job_log_entry_without_reverse_relation=held_job_result.job_log_entries.first(),
                )

                archive_job_result = self.run_archive_old_records_job(force_cascade_delete=force_cascade_delete)

                self.assertJobResultStatus(archive_job_result)
                self.assertTrue(JobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertEqual(JobLogEntry.objects.filter(job_result_id=held_job_result.pk).count(), 2)
                self.assertFalse(ArchivedJobResult.objects.filter(pk=held_job_result.pk).exists())
                self.assertTrue(AnotherExampleModel.objects.filter(pk=referencing_record.pk).exists())
                self.assertIn(
                    "Skipping 1 JobResult records that are still referenced through"
                    " example_app.AnotherExampleModel.job_log_entry_without_reverse_relation ->"
                    " extras.JobLogEntry.job_result. To include them, first delete the referencing"
                    " example_app.AnotherExampleModel records or remove their references.",
                    self.get_job_log_messages(archive_job_result),
                )

                referencing_record.delete()

    @tag("example_app")
    def test_a_dry_run_does_not_count_the_log_entries_of_held_job_results(self):
        from example_app.models import ExampleModel

        held_job_result = self.make_job_result(age_in_days=90, log_entry_count=2)
        ExampleModel.objects.create(name="Archive Dry Run Probe", job_log_entry=held_job_result.job_log_entries.first())
        self.make_job_result(age_in_days=90, log_entry_count=3)

        archive_job_result = self.run_archive_old_records_job(dryrun=True)

        self.assertJobResultStatus(archive_job_result)
        self.assertEqual(archive_job_result.result["extras.JobResult"], 1)
        self.assertEqual(archive_job_result.result["extras.JobLogEntry"], 3)


class FindRelationsOfConcernTestCase(TestCase):
    """Test the relation search that `ArchiveOldRecords` and `LogsCleanup` use to decide what they can delete safely."""

    @tag("example_app")
    def test_relations_are_found_through_the_children_the_job_archives_itself(self):
        from example_app.models import AnotherExampleModel, ExampleModel

        relations = find_relations_of_concern(JobResult, (JobLogEntry, JobConsoleEntry), force_cascade_delete=False)

        self.assertIn(("job_log_entries__more_example_models", AnotherExampleModel), relations.blocking)
        self.assertIn(("job_log_entries__example_models", ExampleModel), relations.cascading)
        self.assertIn(("files", FileProxy), relations.cascading)
        # The children themselves are not a concern, because the job archives them before the job result, but their
        # records are deleted along with it.
        reported_lookups = [lookup for lookup, _ in relations.blocking + relations.cascading]
        self.assertNotIn("job_log_entries", reported_lookups)
        self.assertNotIn("job_console_entries", reported_lookups)
        self.assertEqual(
            relations.followed, [("job_console_entries", JobConsoleEntry), ("job_log_entries", JobLogEntry)]
        )

    @tag("example_app")
    def test_forcing_follows_a_cascade_to_the_blocking_relations_beyond_it(self):
        from example_app.models import AnotherExampleModel, ExampleModel

        relations = find_relations_of_concern(JobResult, (JobLogEntry, JobConsoleEntry), force_cascade_delete=True)

        self.assertIn(("job_log_entries__example_models__more_example_models", AnotherExampleModel), relations.blocking)
        self.assertEqual(relations.cascading, [])
        self.assertIn(("job_log_entries__example_models", ExampleModel), relations.followed)
        self.assertIn(("files", FileProxy), relations.followed)

    @tag("example_app")
    def test_a_foreign_key_without_a_reverse_relation_is_found(self):
        """A `related_name` ending in `+` hides the relation from `_meta.related_objects`, but not from deletion."""
        from example_app.models import AnotherExampleModel

        hidden_field = AnotherExampleModel._meta.get_field("job_log_entry_without_reverse_relation")
        for force_cascade_delete in (False, True):
            with self.subTest(force_cascade_delete=force_cascade_delete):
                relations = find_relations_of_concern(
                    JobResult, (JobLogEntry, JobConsoleEntry), force_cascade_delete=force_cascade_delete
                )

                self.assertIn(("job_log_entries", hidden_field), relations.hidden_blocking)

    def test_a_reference_path_is_described_by_its_foreign_keys(self):
        """Each step is named by its foreign key, or by the generic foreign key for a GenericRelation."""
        self.assertEqual(
            _describe_reference_path(JobResult, "job_log_entries"),
            "extras.JobLogEntry.job_result",
        )
        self.assertEqual(
            _describe_reference_path(JobResult, "job_log_entries__associated_object_metadata"),
            "extras.ObjectMetadata.assigned_object -> extras.JobLogEntry.job_result",
        )

    def test_relations_that_set_a_value_on_delete_are_not_a_concern(self):
        """`Interface.bridge` is `SET_NULL`: deleting the bridge leaves the bridged interfaces in place."""
        for force_cascade_delete in (False, True):
            with self.subTest(force_cascade_delete=force_cascade_delete):
                relations = find_relations_of_concern(Interface, force_cascade_delete=force_cascade_delete)

                reported_lookups = [lookup for found_relations in relations for lookup, _ in found_relations]
                self.assertNotIn("bridged_interfaces", reported_lookups)

    def test_a_forced_cascade_cycle_is_blocking(self):
        """
        `Interface.parent_interface` cascades to child interfaces, whose own children cascade in turn, to any depth.

        A lookup path cannot follow the cycle to every depth, so the records it reaches cannot all be checked, and the
        search does not go round the cycle again.
        """
        unforced_relations = find_relations_of_concern(Interface, force_cascade_delete=False)
        forced_relations = find_relations_of_concern(Interface, force_cascade_delete=True)

        self.assertIn(("child_interfaces", Interface), unforced_relations.cascading)
        self.assertIn(("child_interfaces", Interface), forced_relations.blocking)
        self.assertNotIn(("child_interfaces", Interface), forced_relations.followed)
        all_forced_lookups = [
            lookup for lookup, _ in forced_relations.blocking + forced_relations.cascading + forced_relations.followed
        ]
        self.assertFalse(any(lookup.startswith("child_interfaces__") for lookup in all_forced_lookups))

    def test_a_forced_cascade_into_object_metadata_is_followed(self):
        """
        Every `BaseModel` has GenericRelations to `ObjectMetadata` and `DataCompliance`.

        The cascade into an object change's own metadata is followed rather than held back. The reverse `GenericRel`
        that each model's GenericRelation adds to `ObjectMetadata` and `DataCompliance`, such as
        `associated_object_metadata_circuits_circuit`, is not a relation of concern at all.
        """
        relations = find_relations_of_concern(ObjectChange, force_cascade_delete=True)

        self.assertIn(("associated_object_metadata", ObjectMetadata), relations.followed)
        reported_lookups = [lookup for lookup, _ in relations.blocking + relations.cascading]
        self.assertNotIn("associated_object_metadata", reported_lookups)
        self.assertFalse(
            any(
                segment.startswith(("associated_object_metadata_", "associated_data_compliance_"))
                for lookup in reported_lookups
                for segment in lookup.split("__")
            ),
            reported_lookups,
        )
