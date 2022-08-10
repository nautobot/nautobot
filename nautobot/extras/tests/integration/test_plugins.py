import json
import os
import tempfile
from unittest import skipIf

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.circuits.models import (
    Circuit,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.extras.choices import WebhookHttpMethodChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Status, Webhook
from nautobot.utilities.testing.integration import SeleniumTestCase

from example_plugin.models import ExampleModel


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginWebhookTest(SeleniumTestCase):
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
            "plugins-api:example_plugin-api:examplemodel_webhook"
        )
        self.webhook = Webhook.objects.create(
            name="ExampleModel",
            type_create=True,
            type_update=True,
            type_delete=True,
            payload_url=self.url,
            http_method=WebhookHttpMethodChoices.METHOD_GET,
            http_content_type="application/json",
        )
        self.example_ct = ContentType.objects.get_for_model(ExampleModel)
        self.webhook.content_types.set([self.example_ct])

    def update_headers(self, new_header):
        """
        Update webhook additional headers with the name of the running test.
        """
        headers = f"Test-Name: {new_header}"
        self.webhook.additional_headers = headers
        self.webhook.validated_save()

    def test_plugin_webhook_create(self):
        """
        Test that webhooks are correctly triggered by a plugin model create.
        """
        self.clear_worker()
        self.update_headers("test_plugin_webhook_create")
        # Make change to model
        with web_request_context(self.user):
            ExampleModel.objects.create(name="foo", number=100)
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_create")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_create"))

    def test_plugin_webhook_update(self):
        """
        Test that webhooks are correctly triggered by a plugin model update.
        """
        self.clear_worker()
        self.update_headers("test_plugin_webhook_update")
        obj = ExampleModel.objects.create(name="foo", number=100)

        # Make change to model
        with web_request_context(self.user):
            obj.number = 200
            obj.validated_save()
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_update")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_update"))

    def test_plugin_webhook_delete(self):
        """
        Test that webhooks are correctly triggered by a plugin model delete.
        """
        self.clear_worker()
        self.update_headers(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete"))
        obj = ExampleModel.objects.create(name="foo", number=100)

        # Make change to model
        with web_request_context(self.user):
            obj.delete()
        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete")))
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_delete"))

    def test_plugin_webhook_with_body(self):
        """
        Verify that webhook body_template is correctly used.
        """
        self.clear_worker()
        self.update_headers("test_plugin_webhook_with_body")

        self.webhook.body_template = '{"message": "{{ event }}"}'
        self.webhook.save()

        # Make change to model
        with web_request_context(self.user):
            ExampleModel.objects.create(name="bar", number=100)

        self.wait_on_active_tasks()
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body")))
        with open(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body"), "r") as f:
            self.assertEqual(json.loads(f.read()), {"message": "created"})
        os.remove(os.path.join(tempfile.gettempdir(), "test_plugin_webhook_with_body"))


class PluginDocumentationTest(SeleniumTestCase):
    """
    Integration tests for ensuring plugin provided docs are supported.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_object_edit_help_provided(self):
        """The ExampleModel object provides model documentation, this test ensures the help link is rendered."""
        self.browser.visit(f'{self.live_server_url}{reverse("plugins:example_plugin:examplemodel_add")}')

        self.assertTrue(self.browser.links.find_by_partial_href("example_plugin/docs/models/examplemodel.html"))

    def test_object_edit_help_not_provided(self):
        """The AnotherExampleModel object doesn't provide model documentation, this test ensures no help link is provided."""
        self.browser.visit(f'{self.live_server_url}{reverse("plugins:example_plugin:anotherexamplemodel_add")}')

        self.assertFalse(self.browser.links.find_by_partial_href("example_plugin/docs/models/anotherexamplemodel.html"))


class PluginReturnUrlTestCase(SeleniumTestCase):
    """
    Integration tests for reversing plugin return urls.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def test_plugin_return_url(self):
        """This test ensures that plugins return url for new objects is the list view."""
        self.browser.visit(f'{self.live_server_url}{reverse("plugins:example_plugin:examplemodel_add")}')

        form = self.browser.find_by_tag("form")

        # Check that the Cancel button is a link to the examplemodel_list view.
        element = form.first.links.find_by_text("Cancel").first
        self.assertEqual(
            element["href"], f'{self.live_server_url}{reverse("plugins:example_plugin:examplemodel_list")}'
        )


class PluginTabsTestCase(SeleniumTestCase):
    """
    Integration tests for extra object detail UI tabs.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def test_circuit_detail_tab(self):
        provider = Provider.objects.create(name="Test Provider", slug="test-provider", asn=12345)
        ProviderNetwork.objects.create(
            name="Test Provider Network",
            slug="test-provider-network",
            provider=provider,
        )
        circuit_type = CircuitType.objects.create(name="Test Circuit Type", slug="test-circuit-type")
        active_status = Status.objects.get_for_model(Circuit).get(slug="active")
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            type=circuit_type,
            status=active_status,
        )
        # Visit the circuit's detail page and check that the tab is visible
        self.browser.visit(f'{self.live_server_url}{reverse("circuits:circuit", args=[str(circuit.pk)])}')
        self.assertTrue(self.browser.is_text_present("Plugin Tab"))
        # Visit the tab link and check the view content
        self.browser.links.find_by_partial_text("Plugin Tab")[0].click()
        self.assertTrue(
            self.browser.is_text_present(
                f"I am some content for the example plugin's circuit ({str(circuit.pk)}) detail tab."
            )
        )

    def test_device_detail_tab(self):
        """
        This test checks that both plugin device tabs from the example plugin are visible and render correctly.
        """
        # Set up the required objects:
        device = create_test_device("Test Device")
        # Visit the device's detail page and check that the tab is visible
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:device", args=[str(device.pk)])}')
        for tab_i in [1, 2]:
            self.assertTrue(self.browser.is_text_present(f"Plugin Tab {tab_i}"))
            # Visit the tab link and check the view content
            self.browser.links.find_by_partial_text(f"Plugin Tab {tab_i}")[0].click()
            self.assertTrue(
                self.browser.is_text_present(
                    f"I am some content for the example plugin's device ({str(device.pk)}) detail tab {tab_i}."
                )
            )
