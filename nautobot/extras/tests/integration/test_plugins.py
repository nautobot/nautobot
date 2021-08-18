import json
import os
import tempfile
from unittest import skipIf

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse


from nautobot.extras.choices import WebhookHttpMethodChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Webhook
from nautobot.utilities.testing.integration import SplinterTestCase

from dummy_plugin.models import DummyModel


@skipIf(
    "dummy_plugin" not in settings.PLUGINS,
    "dummy_plugin not in settings.PLUGINS",
)
class PluginWebhookTest(SplinterTestCase):
    """
    This test case proves that plugins can use the webhook functions when making changes on a model.

    Because webhooks use celery a class variable is set to True called `requires_celery`. This starts
    a celery instance in a separate thread.
    """

    requires_celery = True

    def setUp(self):
        super().setUp()
        for f in os.listdir("/tmp"):
            if f.startswith("test_plugin_webhook_"):
                os.remove(os.path.join("/tmp", f))

        self.url = f"http://localhost:{self.server_thread.port}" + reverse(
            "plugins-api:dummy_plugin-api:dummymodel_webhook"
        )
        self.webhook = Webhook.objects.create(
            name="DummyModel",
            type_create=True,
            type_update=True,
            type_delete=True,
            payload_url=self.url,
            http_method=WebhookHttpMethodChoices.METHOD_GET,
            http_content_type="application/json",
        )
        self.dummy_ct = ContentType.objects.get_for_model(DummyModel)
        self.webhook.content_types.set([self.dummy_ct])

    def update_headers(self, new_header):
        """
        Update webhook additional headers with the name of the running test.
        """
        headers = f"Test-Name: {new_header}"
        self.webhook.additional_headers = headers
        self.webhook.validated_save()

    def test_plugin_webhook_create(self):
        """
        Test `process_webhook` from a model create.
        """
        self.clear_worker()
        self.update_headers("test_plugin_webhook_create")
        # Make change to model
        with web_request_context(self.user):
            DummyModel.objects.create(name="foo", number=100)
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_create")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_create"))

    def test_plugin_webhook_update(self):
        """
        Test `process_webhook` from a model update.
        """
        self.clear_worker()
        self.update_headers("test_plugin_webhook_update")
        obj = DummyModel.objects.create(name="foo", number=100)

        # Make change to model
        with web_request_context(self.user):
            obj.number = 200
            obj.validated_save()
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_update")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_update"))

    def test_plugin_webhook_delete(self):
        """
        Test `process_webhook` from a model delete.
        """
        self.clear_worker()
        self.update_headers(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete"))
        obj = DummyModel.objects.create(name="foo", number=100)

        # Make change to model
        with web_request_context(self.user):
            obj.delete()
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete"))

    def test_plugin_webhook_with_body(self):
        self.clear_worker()
        self.update_headers("test_plugin_webhook_with_body")

        self.webhook.body_template = '{"message": "{{ event }}"}'
        self.webhook.save()

        # Make change to model
        with web_request_context(self.user):
            DummyModel.objects.create(name="bar", number=100)

        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body")))
        with open(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body"), "r") as f:
            self.assertEqual(json.loads(f.read()), {"message": "created"})
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body"))
