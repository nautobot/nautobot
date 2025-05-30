from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.core.celery import app
from nautobot.core.testing import get_job_class_and_model, TransactionTestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.models import (
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.context_managers import (
    deferred_change_logging_for_bulk_operation,
    web_request_context,
)
from nautobot.extras.models import JobHook, Status, Webhook
from nautobot.extras.utils import bulk_delete_with_bulk_change_logging

# Use the proper swappable User model
User = get_user_model()


class WebRequestContextTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jacob",
            email="jacob@example.com",
            password="top_secret",  # noqa: S106  # hardcoded-password-func-arg -- ok as this is test code only
        )

        location_ct = ContentType.objects.get_for_model(Location)
        MOCK_URL = "http://localhost/"
        MOCK_SECRET = "LOOKATMEIMASECRETSTRING"  # noqa: S105  # hardcoded-password-string -- ok as this is test code

        webhooks = Webhook.objects.bulk_create(
            (
                Webhook(
                    name="Location Create Webhook",
                    type_create=True,
                    payload_url=MOCK_URL,
                    secret=MOCK_SECRET,
                ),
            )
        )
        for webhook in webhooks:
            webhook.content_types.set([location_ct])

        app.control.purge()  # Begin each test with an empty queue

    def test_user_object_type_error(self):
        with self.assertRaises(TypeError):
            with web_request_context("a string is not a user object"):
                pass

    def test_change_log_created(self):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()

        location = Location.objects.get(name="Test Location 1")
        oc_list = get_changes_for_model(location).order_by("pk").filter(changed_object_id=location.id)
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].changed_object, location)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)

    @mock.patch("nautobot.extras.jobs.enqueue_job_hooks", return_value=(True, None))
    @mock.patch("nautobot.extras.context_managers.enqueue_webhooks", return_value=None)
    def test_create_then_delete(self, mock_enqueue_webhooks, mock_enqueue_job_hooks):
        """Test that a create followed by a delete is logged as two changes"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location_pk = location.pk
            location.delete()

        location = Location.objects.filter(pk=location_pk)
        self.assertFalse(location.exists())
        oc_list = get_changes_for_model(Location).filter(changed_object_id=location_pk).order_by("time")
        self.assertEqual(len(oc_list), 2)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc_list[1].action, ObjectChangeActionChoices.ACTION_DELETE)
        mock_enqueue_job_hooks.assert_has_calls(
            [
                mock.call(oc_list[0], may_reload_jobs=True, jobhook_queryset=None),
                mock.call(oc_list[1], may_reload_jobs=False, jobhook_queryset=None),
            ],
        )
        mock_enqueue_webhooks.assert_has_calls(
            [
                mock.call(oc_list[0], snapshots=oc_list[0].get_snapshots(), webhook_queryset=None),
                mock.call(oc_list[1], snapshots=oc_list[1].get_snapshots(), webhook_queryset=None),
            ]
        )

    def test_update_then_delete(self):
        """Test that an update followed by a delete is logged as a single delete"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location_pk = location.pk
        with web_request_context(self.user):
            location.description = "changed"
            location.save()
            location.delete()

        location = Location.objects.filter(pk=location_pk)
        self.assertFalse(location.exists())
        oc_list = get_changes_for_model(Location).filter(changed_object_id=location_pk)
        self.assertEqual(len(oc_list), 2)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_DELETE)
        snapshots = oc_list[0].get_snapshots()
        self.assertIsNotNone(snapshots["prechange"])
        self.assertIsNone(snapshots["postchange"])
        self.assertIsNone(snapshots["differences"]["added"])
        self.assertEqual(snapshots["differences"]["removed"]["description"], "")

    def test_create_then_update(self):
        """Test that a create followed by an update is logged as a single create"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location.description = "changed"
            location.save()

        oc_list = get_changes_for_model(location).filter(changed_object_id=location.id)
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)
        snapshots = oc_list[0].get_snapshots()
        self.assertIsNone(snapshots["prechange"])
        self.assertIsNotNone(snapshots["postchange"])
        self.assertIsNone(snapshots["differences"]["removed"])
        self.assertEqual(snapshots["differences"]["added"]["description"], "changed")

    def test_delete_then_create(self):
        """Test that a delete followed by a create is logged as a single update"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        pk_list = []
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location_pk = location.pk
            pk_list.append(location.pk)
        with web_request_context(self.user):
            location.delete()
            location = Location.objects.create(
                pk=location_pk,
                name="Test Location 1",
                location_type=location_type,
                status=location_status,
                description="changed",
            )
            pk_list.append(location.pk)

        oc_list = get_changes_for_model(location).filter(changed_object_id__in=pk_list)
        self.assertEqual(len(oc_list), 2)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_UPDATE)
        snapshots = oc_list[0].get_snapshots()
        self.assertIsNotNone(snapshots["prechange"])
        self.assertIsNotNone(snapshots["postchange"])
        self.assertSequenceEqual(
            list(snapshots["differences"]["added"].keys()),
            ("created", "description"),
        )
        self.assertEqual(snapshots["differences"]["added"]["description"], "changed")

    def test_change_log_context(self):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user, context_detail="test_change_log_context"):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()

        location = Location.objects.get(name="Test Location 1")
        oc_list = get_changes_for_model(location)
        with self.subTest():
            self.assertEqual(oc_list[0].change_context, ObjectChangeEventContextChoices.CONTEXT_ORM)
        with self.subTest():
            self.assertEqual(oc_list[0].change_context_detail, "test_change_log_context")

    @mock.patch("nautobot.extras.webhooks.process_webhook.apply_async")
    def test_change_webhook_enqueued(self, mock_apply_async):
        """Test that the webhook resides on the queue"""
        with web_request_context(self.user):
            location = Location(
                name="Test Location 2",
                location_type=LocationType.objects.get(name="Campus"),
                status=Status.objects.get_for_model(Location).first(),
            )
            location.save()

        # Verify that a job was queued for the object creation webhook
        oc_list = get_changes_for_model(location)
        mock_apply_async.assert_called_once()
        call_args = mock_apply_async.call_args.kwargs["args"]
        self.assertEqual(8, len(call_args), call_args)
        self.assertEqual(call_args[0], Webhook.objects.get(type_create=True).pk)
        self.assertEqual(call_args[1], oc_list[0].object_data_v2)
        self.assertEqual(call_args[2], "location")
        self.assertEqual(call_args[3], "create")
        self.assertIsInstance(call_args[4], str)  # str(timezone.now())
        self.assertEqual(call_args[5], self.user.username)
        self.assertEqual(call_args[6], oc_list[0].request_id)
        self.assertEqual(call_args[7], oc_list[0].get_snapshots())

    def test_web_request_context_raises_exception_correctly(self):
        """
        Test implemented to ensure the fix for https://github.com/nautobot/nautobot/issues/7358 is working as intended.
        The operation should raise and allow an exception to be passed through instead of raising an
        AttributeError: 'NoneType' object has no attribute 'get'"
        """
        valid_location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        invalid_location_type = LocationType(name="rackgroup")
        with self.assertRaises(ValidationError):
            with web_request_context(self.user, context_detail="test_web_request_context_raises_exception_correctly"):
                # These operations should generate some ObjectChange records to test the code path that was causing the reported issue.
                location = Location(name="Test Location 1", location_type=valid_location_type, status=location_status)
                location.save()
                location.description = "changed"
                location.save()
                # Location type name is not allowed to be "rackgroup" (reserved name), so this should raise an exception.
                invalid_location_type.validated_save()


class WebRequestContextTransactionTestCase(TransactionTestCase):
    def test_change_log_thread_safe(self):
        """
        Emulate a race condition where the change log signal handler
        is disconnected while there is a pending object change.
        """
        user = User.objects.create(username="test-user123")
        with web_request_context(user, context_detail="test_change_log_context"):
            with web_request_context(user, context_detail="test_change_log_context"):
                status1 = Status.objects.create(name="Test Status 1")
            status2 = Status.objects.create(name="Test Status 2")

        self.assertEqual(get_changes_for_model(status1).count(), 1)
        self.assertEqual(get_changes_for_model(status2).count(), 1)


class BulkEditDeleteChangeLogging(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jacob",
            email="jacob@example.com",
            password="top_secret",  # noqa: S106  # hardcoded-password-func-arg -- ok as this is test code only
        )

    def test_change_log_created(self):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            with deferred_change_logging_for_bulk_operation():
                location = Location(name="Test Location 1", location_type=location_type, status=location_status)
                location.save()

        location = Location.objects.get(name="Test Location 1")
        oc_list = get_changes_for_model(location).order_by("pk").filter(changed_object_id=location.id)
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].changed_object, location)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)

    def test_delete(self):
        """Test that deletes raise an exception"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with self.assertRaises(ValueError):
            with web_request_context(self.user):
                with deferred_change_logging_for_bulk_operation():
                    location = Location(name="Test Location 1", location_type=location_type, status=location_status)
                    location.save()
                    location.delete()

    def test_bulk_delete_has_user_in_change_log(self):
        """Test that the bulk delete operation adds the user to the change log"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location_pk = location.pk
            location_qs = Location.objects.filter(pk=location_pk)
            bulk_delete_with_bulk_change_logging(location_qs)

        oc_list = get_changes_for_model(location)
        self.assertEqual(len(oc_list), 2)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc_list[0].user, self.user)
        self.assertEqual(oc_list[0].user_name, self.user.username)

    def test_create_then_update(self):
        """Test that a create followed by an update is logged as a single create"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user):
            with deferred_change_logging_for_bulk_operation():
                location = Location(name="Test Location 1", location_type=location_type, status=location_status)
                location.save()
                location.description = "changed"
                location.save()

        oc_list = get_changes_for_model(location).filter(changed_object_id=location.id)
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)
        snapshots = oc_list[0].get_snapshots()
        self.assertIsNone(snapshots["prechange"])
        self.assertIsNotNone(snapshots["postchange"])
        self.assertIsNone(snapshots["differences"]["removed"])
        self.assertEqual(snapshots["differences"]["added"]["description"], "changed")

    @mock.patch("nautobot.extras.jobs.import_jobs")
    def test_bulk_edit(self, mock_import_jobs):
        """Test that edits to multiple objects are correctly logged"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        locations = [
            Location(name=f"Test Location {i}", location_type=location_type, status=location_status)
            for i in range(1, 4)
        ]
        Location.objects.bulk_create(locations)
        # Create a JobHook that applies to Locations
        _, job_model = get_job_class_and_model("job_hook_receiver", "TestJobHookReceiverLog")
        mock_import_jobs.assert_called_once()
        mock_import_jobs.reset_mock()
        job_hook = JobHook.objects.create(name="JobHookTest", type_update=True, job=job_model)
        job_hook.content_types.set([ContentType.objects.get_for_model(Location)])

        pk_list = []
        with web_request_context(self.user):
            with deferred_change_logging_for_bulk_operation():
                for location in locations:
                    location.description = "changed"
                    location.save()
                    pk_list.append(location.id)

        oc_list = get_changes_for_model(Location).filter(changed_object_id__in=pk_list)
        self.assertEqual(len(oc_list), 3)
        for oc in oc_list:
            self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
            snapshots = oc.get_snapshots()
            self.assertIsNone(snapshots["prechange"])
            self.assertIsNotNone(snapshots["postchange"])
            self.assertIsNone(snapshots["differences"]["removed"])
            self.assertEqual(snapshots["differences"]["added"]["description"], "changed")

        # Check for regression of https://github.com/nautobot/nautobot/issues/6203
        mock_import_jobs.assert_called_once()

    def test_bulk_edit_device_type_software_image_file(self):
        """Test that bulk edits to null does not cause integrity error"""
        manufacturer = Manufacturer.objects.create(name="Test")
        platform = Platform.objects.create(name="Test")
        software_status = Status.objects.get_for_model(SoftwareVersion).first()
        software_version = SoftwareVersion.objects.create(version="1.0.0", platform=platform, status=software_status)
        software_image_file = SoftwareImageFile.objects.create(
            image_file_name="test.iso", software_version=software_version, status=software_status
        )
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="test123")
        device_type.software_image_files.set([software_image_file])
        oc_list_1 = list(get_changes_for_model(DeviceTypeToSoftwareImageFile))
        with web_request_context(self.user):
            with deferred_change_logging_for_bulk_operation():
                device_type.software_image_files.set([])
                device_type.save()

        oc_list_2 = list(get_changes_for_model(DeviceTypeToSoftwareImageFile))
        self.assertEqual(len(oc_list_2) - len(oc_list_1), 1)
        self.assertEqual(oc_list_2[0].action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertIsNotNone(oc_list_2[0].changed_object_id)
        self.assertEqual(oc_list_2[0].user, self.user)
        self.assertEqual(oc_list_2[0].user_name, self.user.username)

    def test_change_log_context(self):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        with web_request_context(self.user, context_detail="test_change_log_context"):
            with deferred_change_logging_for_bulk_operation():
                location = Location(name="Test Location 1", location_type=location_type, status=location_status)
                location.save()

        location = Location.objects.get(name="Test Location 1")
        oc_list = get_changes_for_model(location)
        with self.subTest():
            self.assertEqual(oc_list[0].change_context, ObjectChangeEventContextChoices.CONTEXT_ORM)
        with self.subTest():
            self.assertEqual(oc_list[0].change_context_detail, "test_change_log_context")
