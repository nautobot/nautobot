from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.core.celery import app
from nautobot.core.testing import TransactionTestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.context_managers import (
    deferred_change_logging_for_bulk_operation,
    web_request_context,
)
from nautobot.extras.models import Status, Webhook
from nautobot.extras.models.change_logging import ObjectChange
from nautobot.extras.models.contacts import Contact, ContactAssociation
from nautobot.extras.models.models import Note
from nautobot.extras.models.roles import Role
from nautobot.extras.models.tags import Tag

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
        oc_list = get_changes_for_model(location).order_by("pk")
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].changed_object, location)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)

    def test_create_then_delete(self):
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
        oc_list = get_changes_for_model(Location).filter(changed_object_id=location_pk)
        self.assertEqual(len(oc_list), 2)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc_list[1].action, ObjectChangeActionChoices.ACTION_CREATE)

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

        oc_list = get_changes_for_model(location)
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
        with web_request_context(self.user):
            location = Location(name="Test Location 1", location_type=location_type, status=location_status)
            location.save()
            location_pk = location.pk
        with web_request_context(self.user):
            location.delete()
            location = Location.objects.create(
                pk=location_pk,
                name="Test Location 1",
                location_type=location_type,
                status=location_status,
                description="changed",
            )

        oc_list = get_changes_for_model(location)
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

    def test_change_webhook_enqueued(self):
        """Test that the webhook resides on the queue"""
        # TODO(john): come back to this with a way to actually do it without a running worker
        # The celery inspection API expects to be able to communicate with at least 1 running
        # worker and there does not appear to be an easy way to look into the queues directly.
        # with web_request_context(self.user):
        #    site = Site(name="Test Site 2")
        #    site.save()

        # Verify that a job was queued for the object creation webhook
        # site = Site.objects.get(name="Test Site 2")

        # self.assertEqual(job.args[0], Webhook.objects.get(type_create=True))
        # self.assertEqual(job.args[1]["id"], str(site.pk))
        # self.assertEqual(job.args[2], "site")


class WebRequestContextTransactionTestCase(TransactionTestCase):
    def test_change_log_thread_safe(self):
        """
        Emulate a race condition where the change log signal handler
        is disconnected while there is a pending object change.
        """
        user = User.objects.create(username="test-user123")
        with web_request_context(user, context_detail="test_change_log_context"):
            with web_request_context(user, context_detail="test_change_log_context"):
                Status.objects.create(name="Test Status 1")
            Status.objects.create(name="Test Status 2")

        self.assertEqual(get_changes_for_model(Status).count(), 2)


class BulkEditDeleteChangeLogging(TestCase):
    def setUp(self):
        super().setUp()
        roles = Role.objects.get_for_model(ContactAssociation)
        statuses = Status.objects.get_for_model(ContactAssociation)
        self.tags = [Tag.objects.create(name=f"Tag {idx}") for idx in range(2)]
        self.notes_created = []
        self.contact_association_created = []
        for idx, tag in enumerate(self.tags):
            note = Note.objects.create(note="Note to delete", assigned_object=tag)
            self.notes_created.append(note.pk)
            contact_association = ContactAssociation.objects.create(
                contact=Contact.objects.all()[idx],
                associated_object=tag,
                role=roles[1],
                status=statuses[1],
            )
            self.contact_association_created.append(contact_association.pk)
        self.user = User.objects.create(username="nautobotuser")

    def _assert_change_logging_created(self, action):
        objs = self.tags
        object_change_queryset = ObjectChange.objects.filter(
            action=action,
            change_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
        )
        self.assertEqual(object_change_queryset.count(), len(objs))
        self.assertTrue(object_change_queryset.filter(changed_object_id=objs[0].pk).exists())
        self.assertTrue(object_change_queryset.filter(changed_object_id=objs[1].pk).exists())

    def test_bulk_update_with_changelogging(self):
        with web_request_context(self.user, context_detail="test_change_log_context"):
            with deferred_change_logging_for_bulk_operation(
                objs=self.tags, user=self.user, action=ObjectChangeActionChoices.ACTION_UPDATE
            ):
                for tag in self.tags:
                    tag.name = f"{tag.name}-updated"
                    tag.save()
        self._assert_change_logging_created(action=ObjectChangeActionChoices.ACTION_UPDATE)

    def test_bulk_delete(self):
        tags_pks = [tag.pk for tag in self.tags]
        with web_request_context(self.user, context_detail="test_change_log_context"):
            with deferred_change_logging_for_bulk_operation(
                objs=self.tags, user=self.user, action=ObjectChangeActionChoices.ACTION_DELETE
            ):
                self._assert_change_logging_created(action=ObjectChangeActionChoices.ACTION_DELETE)
                Tag.objects.filter(pk__in=tags_pks).delete()
        self.assertFalse(Note.objects.filter(pk__in=self.notes_created))
        self.assertFalse(ContactAssociation.objects.filter(pk__in=self.contact_association_created))
