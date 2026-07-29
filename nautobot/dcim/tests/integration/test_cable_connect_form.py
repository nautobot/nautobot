import time

from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Interface
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.extras.models import Status


class CableConnectFormTestCase(SeleniumTestCase):
    """
    Integration test for the unified `cable_add` form (reached via the legacy `<port>_connect`
    URLs, which now redirect into it). Checks:

     - The B-side termination dropdown's Select2 API call excludes terminations already chosen on
       any other lane — initially the A-side termination, and later anything picked on B-side
       lanes too.
     - Changing the B-side parent (Device, Circuit, PowerPanel, ...) clears the previously
       selected B-side termination value.
    """

    def test_js_functionality(self):
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Two devices, three interfaces on Device 1, one interface on Device 2 so it shows up in
        # the `has_interfaces=True`-filtered Device parent dropdown.
        device1 = create_test_device("Device 1")
        device2 = create_test_device("Device 2")
        interface_status = Status.objects.get_for_model(Interface).first()
        interface1 = Interface.objects.create(device=device1, name="Interface 1", status=interface_status)
        Interface.objects.create(device=device1, name="Interface 2", status=interface_status)
        Interface.objects.create(device=device1, name="Interface 3", status=interface_status)
        Interface.objects.create(device=device2, name="Interface A", status=interface_status)

        # The `<port>_connect` URL redirects into the unified `cable_add` form with A-side
        # identity pre-populated in the query string.
        cable_connect_form_url = reverse(
            "dcim:interface_connect", kwargs={"termination_a_id": interface1.pk, "termination_b_type": "interface"}
        )
        self.browser.visit(f"{self.live_server_url}{cable_connect_form_url}")

        # The B-side lane (connector 1) parent field is `id_b_conn_1_parent` (Device).
        # Click its label to focus the field, then click to open the Select2 dropdown.
        self.browser.find_by_xpath("//label[@for='id_b_conn_1_parent']").click()
        self.browser.driver.switch_to.active_element.click()
        time.sleep(1)
        # Choose 'Device 1' from the dropdown.
        self.browser.find_by_xpath(
            "//ul[@id='select2-id_b_conn_1_parent-results']"
            "/li[contains(@class,'select2-results__option') and contains(text(),'Device 1')]"
        ).click()

        # Open the B-side termination dropdown.
        self.browser.find_by_xpath("//label[@for='id_b_conn_1_termination']").click()
        self.browser.driver.switch_to.active_element.click()
        time.sleep(1)

        # Verify Interface 1 (already chosen as the A-side termination) is excluded from the
        # B-side termination choices; only Interface 2 and Interface 3 should appear.
        select2_results = self.browser.find_by_xpath(
            "//ul[@id='select2-id_b_conn_1_termination-results']/li[contains(@class,'select2-results__option')]"
        )
        self.assertEqual(2, len(select2_results))
        self.assertEqual("Interface 2", select2_results[0].text)
        self.assertEqual("Interface 3", select2_results[1].text)

        # Pick 'Interface 2' as the B-side termination.
        self.browser.find_by_xpath(
            "//ul[@id='select2-id_b_conn_1_termination-results']"
            "/li[contains(@class,'select2-results__option') and contains(text(),'Interface 2')]"
        ).click()
        time.sleep(0.5)

        # Ensure Interface 2 is now the selected value of the underlying <select>. Use jQuery's
        # `:selected` (property-based) rather than xpath `[@selected]` (attribute-based) — Select2
        # updates the .selected property without necessarily mirroring it into the markup.
        self.assertEqual(
            "Interface 2",
            self.browser.evaluate_script("$('#id_b_conn_1_termination option:selected').text()"),
        )

        # Change the B-side parent to 'Device 2'.
        self.browser.find_by_xpath("//label[@for='id_b_conn_1_parent']").click()
        self.browser.driver.switch_to.active_element.click()
        time.sleep(1)
        self.browser.find_by_xpath(
            "//ul[@id='select2-id_b_conn_1_parent-results']"
            "/li[contains(@class,'select2-results__option') and contains(text(),'Device 2')]"
        ).click()
        time.sleep(0.5)

        # The previously selected Interface 2 should now be cleared.
        self.assertFalse(self.browser.evaluate_script("$('#id_b_conn_1_termination').val()"))
