
from django.test import tag
from django.urls import reverse

from nautobot.circuits.models import (
    Circuit,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from nautobot.core.testing.integration import ObjectDetailsMixin, SeleniumTestCase
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.extras.models import Status


@tag("example_app")
class AppDocumentationTest(SeleniumTestCase):
    """
    Integration tests for ensuring App provided docs are supported.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_object_edit_help_provided(self):
        """The ExampleModel object provides model documentation, this test ensures the help link is rendered."""
        self.browser.visit(f"{self.live_server_url}{reverse('plugins:example_app:examplemodel_add')}")
        self.assertTrue(self.browser.links.find_by_partial_href("docs/example-app/models/examplemodel.html"))

    def test_object_edit_help_not_provided(self):
        """The AnotherExampleModel object doesn't provide model documentation, this test ensures no help link is provided."""
        self.browser.visit(f"{self.live_server_url}{reverse('plugins:example_app:anotherexamplemodel_add')}")

        self.assertFalse(self.browser.links.find_by_partial_href("/docs/example-app/models/anotherexamplemodel.html"))


@tag("example_app")
class AppReturnUrlTestCase(SeleniumTestCase):
    """
    Integration tests for reversing App return urls.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_app_return_url(self):
        """This test ensures that Apps return url for new objects is the list view."""
        self.browser.visit(f"{self.live_server_url}{reverse('plugins:example_app:examplemodel_add')}")

        form = self.browser.find_by_tag("form")

        # Check that the Cancel button is a link to the examplemodel_list view.
        element = form.first.links.find_by_partial_text("Cancel").first
        self.assertEqual(element["href"], f"{self.live_server_url}{reverse('plugins:example_app:examplemodel_list')}")


@tag("example_app")
class AppTabsTestCase(SeleniumTestCase, ObjectDetailsMixin):
    """
    Integration tests for extra object detail UI tabs.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_circuit_detail_tab(self):
        provider = Provider.objects.create(name="Test Provider", asn=12345)
        ProviderNetwork.objects.create(
            name="Test Provider Network",
            provider=provider,
        )
        circuit_type = CircuitType.objects.create(name="Test Circuit Type")
        status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            circuit_type=circuit_type,
            status=status,
        )
        # Visit the circuit's detail page and check that the tab is visible
        self.browser.visit(f"{self.live_server_url}{reverse('circuits:circuit', args=[str(circuit.pk)])}")

        # Assert if tab can be found
        tab_link = self.get_tab_link("Example App Tab")
        self.assertTrue(tab_link)

        # Navigate to this tab
        tab_link.click()
        self.assertTrue(
            self.browser.is_text_present(
                f"I am some content for the Example App's circuit ({circuit.pk!s}) detail tab."
            )
        )

    def test_device_detail_tab(self):
        """
        This test checks that both app device tabs from the Example App are visible and render correctly.
        """
        # Set up the required objects:
        device = create_test_device("Test Device")
        # Visit the device's detail page and check that the tab is visible
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:device', args=[str(device.pk)])}")
        for tab_i in [1, 2]:
            tab_link = self.get_tab_link(f"Example App Tab {tab_i}")
            self.assertTrue(tab_link)

            # Visit the tab link and check the view content
            tab_link.click()
            self.assertTrue(
                self.browser.is_text_present(
                    f"I am some content for the Example App's device ({device.pk!s}) detail tab {tab_i}."
                )
            )
