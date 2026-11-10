from unittest import mock
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.core.celery import app
from nautobot.core.models.utils import serialize_object_v2
from nautobot.core.testing import get_job_class_and_model, TransactionTestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    Interface,
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
from nautobot.extras.models import Contact, ContactAssociation, JobHook, Note, Role, Status, Tag, Webhook
from nautobot.extras.utils import bulk_delete_with_bulk_change_logging
from nautobot.tenancy.models import Tenant, TenantGroup

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

    def test_create_then_delete_of_taggable_object(self):
        """Test that a create followed by a delete of a taggable object is logged as two changes"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        tag = Tag.objects.create(name="Deferred Create Delete Tag")
        tag.content_types.add(ContentType.objects.get_for_model(Location))

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                location = Location(name="Test Location 1", location_type=location_type, status=location_status)
                location.save()
                location.tags.add(tag)
                location_pk = location.pk
                location.delete()

        oc_list = get_changes_for_model(Location).filter(request_id=change_id).order_by("time")
        self.assertEqual(
            [oc.action for oc in oc_list],
            [ObjectChangeActionChoices.ACTION_CREATE, ObjectChangeActionChoices.ACTION_DELETE],
        )
        for oc in oc_list:
            self.assertEqual(oc.changed_object_id, location_pk)
            self.assertEqual(oc.object_data_v2["id"], str(location_pk))
        self.assertEqual(oc_list[1].object_data["tags"], [tag.name])

    def test_delete_of_taggable_object(self):
        """Test that deleting a taggable object under deferred change logging logs its id, url and tags"""
        tag = Tag.objects.create(name="Deferred Delete Tag")
        tag.content_types.add(ContentType.objects.get_for_model(Tenant))
        tenant = Tenant.objects.create(name="Deferred Delete Tenant")
        tenant.tags.add(tag)
        tenant_pk = tenant.pk
        expected_v2 = serialize_object_v2(tenant)

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                tenant.delete()

        oc = get_changes_for_model(Tenant).get(request_id=change_id)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.changed_object_id, tenant_pk)
        self.assertEqual(oc.object_data["tags"], [tag.name])
        self.assertEqual(oc.object_data_v2["id"], str(tenant_pk))
        self.assertEqual(oc.object_data_v2["url"], expected_v2["url"])
        self.assertEqual(len(oc.object_data_v2["tags"]), 1)

    def test_delete_of_non_taggable_object(self):
        """Test that deleting a non-taggable object under deferred change logging logs its id and url"""
        tenant_group = TenantGroup.objects.create(name="Deferred Delete Tenant Group")
        tenant_group_pk = tenant_group.pk
        expected_v2 = serialize_object_v2(tenant_group)

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                tenant_group.delete()

        oc = get_changes_for_model(TenantGroup).get(request_id=change_id)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.changed_object_id, tenant_group_pk)
        self.assertEqual(oc.object_data_v2["id"], str(tenant_group_pk))
        self.assertEqual(oc.object_data_v2["url"], expected_v2["url"])

    def test_update_then_delete(self):
        """Test that an update followed by a delete under deferred change logging is logged as a single delete"""
        tenant_group = TenantGroup.objects.create(name="Deferred Update Delete Tenant Group")
        tenant_group_pk = tenant_group.pk

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                tenant_group.description = "changed"
                tenant_group.save()
                tenant_group.delete()

        oc = get_changes_for_model(TenantGroup).get(request_id=change_id)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.changed_object_id, tenant_group_pk)
        self.assertEqual(oc.object_data_v2["id"], str(tenant_group_pk))

    def test_create_then_delete_of_non_taggable_object(self):
        """Test that a create followed by a delete under deferred change logging is logged as two changes"""
        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                tenant_group = TenantGroup.objects.create(name="Deferred Create Delete Tenant Group")
                tenant_group_pk = tenant_group.pk
                tenant_group.delete()

        oc_list = get_changes_for_model(TenantGroup).filter(request_id=change_id).order_by("time")
        self.assertEqual(
            [oc.action for oc in oc_list],
            [ObjectChangeActionChoices.ACTION_CREATE, ObjectChangeActionChoices.ACTION_DELETE],
        )
        for oc in oc_list:
            self.assertEqual(oc.changed_object_id, tenant_group_pk)
            self.assertEqual(oc.object_data_v2["id"], str(tenant_group_pk))

    def test_delete_with_cascade(self):
        """Test that components deleted by cascade under deferred change logging are logged with their parent"""
        device = Device.objects.create(
            name="Deferred Cascade Device",
            device_type=DeviceType.objects.first(),
            role=Role.objects.get_for_model(Device).first(),
            status=Status.objects.get_for_model(Device).first(),
            location=Location.objects.filter(
                location_type__content_types=ContentType.objects.get_for_model(Device)
            ).first(),
        )
        device_pk = device.pk
        interface_status = Status.objects.get_for_model(Interface).first()
        for i in range(2):
            Interface.objects.create(
                device=device, name=f"deferred{i}", type=InterfaceTypeChoices.TYPE_1GE_FIXED, status=interface_status
            )
        interface_pks = set(device.interfaces.values_list("pk", flat=True))

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                device.delete()

        device_oc = get_changes_for_model(Device).get(request_id=change_id)
        self.assertEqual(device_oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(device_oc.changed_object_id, device_pk)
        self.assertEqual(device_oc.object_data_v2["id"], str(device_pk))
        interface_ocs = get_changes_for_model(Interface).filter(request_id=change_id)
        self.assertEqual({oc.changed_object_id for oc in interface_ocs}, interface_pks)
        for oc in interface_ocs:
            self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
            self.assertEqual(oc.object_data_v2["id"], str(oc.changed_object_id))
            self.assertEqual(oc.related_object_type, ContentType.objects.get_for_model(Device))
            self.assertEqual(oc.related_object_id, device_pk)

    def test_delete_children_then_parent(self):
        """Test that components deleted before their parent under deferred change logging are logged with their parent"""
        device = Device.objects.create(
            name="Deferred Children Then Parent Device",
            device_type=DeviceType.objects.first(),
            role=Role.objects.get_for_model(Device).first(),
            status=Status.objects.get_for_model(Device).first(),
            location=Location.objects.filter(
                location_type__content_types=ContentType.objects.get_for_model(Device)
            ).first(),
        )
        device_pk = device.pk
        Interface.objects.create(
            device=device,
            name="deferred0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=Status.objects.get_for_model(Interface).first(),
        )
        interface_pks = set(device.interfaces.values_list("pk", flat=True))

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            with deferred_change_logging_for_bulk_operation():
                # Interfaces fetched through the device share its instance, whose pk is cleared by device.delete()
                for interface in device.interfaces.all():
                    interface.delete()
                device.delete()

        device_oc = get_changes_for_model(Device).get(request_id=change_id)
        self.assertEqual(device_oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(device_oc.changed_object_id, device_pk)
        interface_ocs = get_changes_for_model(Interface).filter(request_id=change_id)
        self.assertEqual({oc.changed_object_id for oc in interface_ocs}, interface_pks)
        for oc in interface_ocs:
            self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
            self.assertEqual(oc.related_object_type, ContentType.objects.get_for_model(Device))
            self.assertEqual(oc.related_object_id, device_pk)

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

    def test_bulk_delete_logs_cascade_children(self):
        """Bulk delete should log ObjectChanges for CASCADE-deleted child rows, not just queryset members."""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        parent = Location.objects.create(name="Parent BulkDelete", location_type=location_type, status=location_status)
        child_a = Location.objects.create(
            name="Child A", location_type=location_type, status=location_status, parent=parent
        )
        child_b = Location.objects.create(
            name="Child B", location_type=location_type, status=location_status, parent=parent
        )
        expected_pks = {parent.pk, child_a.pk, child_b.pk}

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            bulk_delete_with_bulk_change_logging(Location.objects.filter(pk=parent.pk))

        delete_changes = get_changes_for_model(Location).filter(
            action=ObjectChangeActionChoices.ACTION_DELETE,
            request_id=change_id,
        )
        self.assertEqual({oc.changed_object_id for oc in delete_changes}, expected_pks)
        for oc in delete_changes:
            self.assertEqual(oc.user, self.user)
            self.assertEqual(oc.user_name, self.user.username)

    def test_bulk_delete_serializes_each_object_once(self):
        """Test that bulk delete does not also serialize deleted objects in the pre_delete signal handler"""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        parent = Location.objects.create(name="Parent BulkDelete", location_type=location_type, status=location_status)
        Location.objects.create(name="Child A", location_type=location_type, status=location_status, parent=parent)
        Location.objects.create(name="Child B", location_type=location_type, status=location_status, parent=parent)

        with mock.patch.object(
            Location, "to_objectchange", autospec=True, side_effect=Location.to_objectchange
        ) as mock_to_objectchange:
            with web_request_context(self.user):
                bulk_delete_with_bulk_change_logging(Location.objects.filter(pk=parent.pk))

        self.assertEqual(mock_to_objectchange.call_count, 3)

    def test_bulk_delete_logs_contact_associations(self):
        """Bulk delete should log an ObjectChange for ContactAssociations the receiver cleans up."""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(
            name="Location With Contact", location_type=location_type, status=location_status
        )
        contact = Contact.objects.create(name="Test Contact")
        assoc_role = Role.objects.get_for_model(ContactAssociation).first()
        assoc_status = Status.objects.get_for_model(ContactAssociation).first()
        association = ContactAssociation.objects.create(
            contact=contact,
            associated_object=location,
            role=assoc_role,
            status=assoc_status,
        )
        association_pk = association.pk

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            bulk_delete_with_bulk_change_logging(Location.objects.filter(pk=location.pk))

        assoc_changes = get_changes_for_model(ContactAssociation).filter(
            action=ObjectChangeActionChoices.ACTION_DELETE, request_id=change_id
        )
        self.assertEqual({oc.changed_object_id for oc in assoc_changes}, {association_pk})
        self.assertEqual(assoc_changes.first().user, self.user)

    def test_bulk_delete_logs_notes(self):
        """Bulk delete should log an ObjectChange for Notes the receiver cleans up."""
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(
            name="Location With Note", location_type=location_type, status=location_status
        )
        note = Note.objects.create(assigned_object=location, user=self.user, note="A note on this location")
        note_pk = note.pk

        change_id = uuid.uuid4()
        with web_request_context(self.user, change_id=change_id):
            bulk_delete_with_bulk_change_logging(Location.objects.filter(pk=location.pk))

        note_changes = get_changes_for_model(Note).filter(
            action=ObjectChangeActionChoices.ACTION_DELETE, request_id=change_id
        )
        self.assertEqual({oc.changed_object_id for oc in note_changes}, {note_pk})
        self.assertEqual(note_changes.first().user, self.user)

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
        self.assertEqual(oc_list_2[0].object_data_v2["id"], str(oc_list_2[0].changed_object_id))
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
