from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.core.celery import app
from nautobot.dcim.models import Site
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Webhook
from nautobot.utilities.utils import get_changes_for_model


# Use the proper swappable User model
User = get_user_model()


class WebRequestContextTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jacob", email="jacob@example.com", password="top_secret")

        site_ct = ContentType.objects.get_for_model(Site)
        MOCK_URL = "http://localhost/"
        MOCK_SECRET = "LOOKATMEIMASECRETSTRING"

        webhooks = Webhook.objects.bulk_create(
            (
                Webhook(
                    name="Site Create Webhook",
                    type_create=True,
                    payload_url=MOCK_URL,
                    secret=MOCK_SECRET,
                ),
            )
        )
        for webhook in webhooks:
            webhook.content_types.set([site_ct])

        app.control.purge()  # Begin each test with an empty queue

    def test_user_object_type_error(self):

        with self.assertRaises(TypeError):
            with web_request_context("a string is not a user object"):
                pass

    def test_change_log_created(self):

        with web_request_context(self.user):
            site = Site(name="Test Site 1")
            site.save()

        site = Site.objects.get(name="Test Site 1")
        oc_list = get_changes_for_model(site).order_by("pk")
        self.assertEqual(len(oc_list), 1)
        self.assertEqual(oc_list[0].changed_object, site)
        self.assertEqual(oc_list[0].action, ObjectChangeActionChoices.ACTION_CREATE)

    def test_change_log_context(self):

        with web_request_context(self.user, context_detail="test_change_log_context"):
            site = Site(name="Test Site 1")
            site.save()

        site = Site.objects.get(name="Test Site 1")
        oc_list = get_changes_for_model(site)
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
