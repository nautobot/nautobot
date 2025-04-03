from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.testing.integration import ObjectDetailsMixin, ObjectsListMixin, SeleniumTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant, TenantGroup


class CircuitTestCase(SeleniumTestCase, ObjectsListMixin, ObjectDetailsMixin):
    """
    Integration test to check circuits related test cases.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        # Termination requirements
        location_type, location_created = LocationType.objects.get_or_create(name="Circuit at Home")
        if location_created:
            location_ct = ContentType.objects.get_for_model(CircuitTermination)
            location_type.content_types.set([location_ct])
            location_type.save()

        location_status = Status.objects.get_for_model(Location).first()
        self.location, _ = Location.objects.get_or_create(
            name="A Test Location",
            status=location_status,
            location_type=location_type,
        )

        self.provider, _ = Provider.objects.get_or_create(name="World Best Cables")
        self.circuit_type, _ = CircuitType.objects.get_or_create(
            name="Yellow Cable",
        )
        self.tenant_group, _ = TenantGroup.objects.get_or_create(name="Family Inc.")
        self.tenant, _ = Tenant.objects.get_or_create(name="Tenant 1", tenant_group=self.tenant_group)

    def create_circuit(self, name):
        circuit, _ = Circuit.objects.get_or_create(
            provider=self.provider,
            cid=name,
            circuit_type=self.circuit_type,
            status=Status.objects.get_for_model(Circuit).first(),
        )
        return circuit

    def test_circuit_create(self):
        cid = "Circuit-test-abc123"
        description = "My Precious Circuit"

        # Create new Circuit from list view
        self.click_navbar_entry("Circuits", "Circuits")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("circuits:circuit_list"))

        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("circuits:circuit_add"))

        # Fill Circuit creation form
        self.fill_select2_field("provider", self.provider.name)
        self.browser.fill("cid", cid)
        self.fill_select2_field("circuit_type", self.circuit_type.name)
        self.fill_select2_field("status", "")  # pick first status
        self.browser.fill("install_date", "2025-01-01")
        self.browser.fill("commit_rate", 192)
        self.browser.fill("description", "My Precious Circuit")
        self.fill_select2_field("tenant_group", "Family Inc.")
        self.fill_select2_field("tenant", "Tenant 1")

        self.click_edit_form_create_button()
        self.assertTrue(self.browser.is_text_present("Created circuit Circuit-test-abc123"))

        # Navigate to Circuit details by filtering the one just created and clicking on it
        self.click_navbar_entry("Circuits", "Circuits")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("circuits:circuit_list"))

        self.apply_filter("circuit_type", "Yellow Cable")
        self.assertEqual(self.objects_list_visible_items, 1)

        self.click_table_link()

        # Assert that value are properly set
        circuit = Circuit.objects.get(cid=cid)
        self.assertIn(self.live_server_url + reverse("circuits:circuit", kwargs={"pk": circuit.pk}), self.browser.url)

        self.assertPanelValue("Circuit", "Circuit ID", cid)
        self.assertPanelValue("Circuit", "Status", "Active")
        self.assertPanelValue("Circuit", "Provider", self.provider.name)
        self.assertPanelValue("Circuit", "Circuit Type", self.circuit_type.name)
        self.assertPanelValue("Circuit", "Tenant", self.tenant.name)
        self.assertPanelValue("Circuit", "Date Installed", "Jan. 1, 2025")
        self.assertPanelValue("Circuit", "Commit Rate (Kbps)", "192")
        self.assertPanelValue("Circuit", "Description", description)

    def test_circuit_create_termination(self):
        circuit = self.create_circuit("Circuit-test-termination")
        sides = ["A", "Z"]
        for side in sides:
            with self.subTest(side=side):
                # Go to Circuit details page
                details_url = self.live_server_url + reverse("circuits:circuit", kwargs={"pk": circuit.pk})
                self.browser.visit(details_url)
                self.assertIn(details_url, self.browser.url)

                # Find and click add termination button
                termination_panel_xpath = f'//*[@id="main"]//div[@class="panel-heading"][contains(normalize-space(), "Termination - {side} Side")]'
                self.browser.find_by_xpath(f'{termination_panel_xpath}//a[normalize-space()="Add"]').click()

                port_speed = ord(side)
                upstream_speed = ord(side) + 10
                xconnect_id = f"xconnect-id-{side}-123"
                pp_info = f"pp-info-{side}-123"
                description = f"{side}-side"

                # Fill termination creation form
                self.fill_select2_field("location", self.location.name)
                self.browser.fill("port_speed", port_speed)
                self.browser.fill("upstream_speed", upstream_speed)
                self.browser.fill("xconnect_id", xconnect_id)
                self.browser.fill("pp_info", pp_info)
                self.browser.fill("description", description)
                self.click_edit_form_create_button()

                self.assertTrue(self.browser.is_text_present(f"Created circuit termination Termination {side}"))

                # Assert that value are properly set
                panel_label = f"Termination - {side} Side"
                self.assertPanelValue(panel_label, "Location", self.location.name)
                self.assertPanelValue(panel_label, "Port Speed (Kbps)", port_speed)
                self.assertPanelValue(panel_label, "Upstream Speed (Kbps)", upstream_speed)
                self.assertPanelValue(panel_label, "Cross-connect ID", xconnect_id)
                self.assertPanelValue(panel_label, "Patch Panel/port(s)", pp_info)
                self.assertPanelValue(panel_label, "Description", description)
