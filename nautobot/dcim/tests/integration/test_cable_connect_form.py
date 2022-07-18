import time

from django.urls import reverse
from selenium.webdriver.common.keys import Keys
from splinter.exceptions import ElementDoesNotExist

from nautobot.dcim.models import Interface
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.utilities.testing.integration import SeleniumTestCase


class CableConnectFormTestCase(SeleniumTestCase):
    """
    Integration test to check:
     - select2 API call limits the choices on the termination_b drop-down on the cable connect form.
     - termination_b_id drop-down choices are cleared when any termination_b dropdown select element value is changed
       (except the name dropdown)
    """

    def test_js_functionality(self):
        """
        This test:
         1 creates some test data (two devices and three interfaces): L35-L39
         2 goes to the cable connect form for interface1: L40-L43
         3 selects the first device in the device drop-down on the termination_b form: L44-L52
         4 selects the first available interface in the "Name" drop-down: L56-L60
           checks the results of the select2 API call (which should have excluded interface1): L63-L66
           this should not be interface1 (this should be excluded) -- it should be interface2: L72-L73
         5 selects a different device: L77-L81
         6 checks to see the "Name" (in this case interface) drop-down is cleared: L82-L84
         7 checks to see if the correct CSS query is loaded for the interface connection form: L87-L91
        """
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        device1 = create_test_device("Device 1")
        create_test_device("Device 2")
        interface1 = Interface.objects.create(device=device1, name="Interface 1")
        Interface.objects.create(device=device1, name="Interface 2")
        Interface.objects.create(device=device1, name="Interface 3")
        cable_connect_form_url = reverse(
            "dcim:interface_connect", kwargs={"termination_a_id": interface1.pk, "termination_b_type": "interface"}
        )
        self.browser.visit(f"{self.live_server_url}{cable_connect_form_url}")
        self.browser.find_by_xpath("(//label[contains(text(),'Device')])[2]").click()

        # select the first device in the device drop-down
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        active_web_element.send_keys(Keys.ENTER)
        # wait for API call to complete
        time.sleep(0.1)
        active_web_element.send_keys(Keys.ENTER)

        # select the first interface in the termination_b_id drop-down
        # this should be "Interface 2"'s PK, as Interface 1 should be excluded
        self.browser.find_by_xpath("(//label[contains(text(),'Name')])[2]").click()
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        active_web_element.send_keys(Keys.ENTER)
        # wait for API call to complete
        time.sleep(0.1)
        select2_results = self.browser.find_by_xpath("//span[@class='select2-results']/ul/li")
        self.assertEqual(2, len(select2_results))
        self.assertEqual("Interface 2", select2_results[0].text)
        self.assertEqual("Interface 3", select2_results[1].text)
        active_web_element.send_keys(Keys.ENTER)

        # wait for DOM to update
        time.sleep(0.1)

        selected = self.browser.find_by_xpath("//select[@id='id_termination_b_id']/option").first
        self.assertEqual("Interface 2", selected.text)

        # test to see whether options are cleared for termination_b_id when another drop-down is changed
        # in this case, from device 1 to device 2
        self.browser.find_by_xpath("(//label[contains(text(),'Device')])[2]").click()
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        active_web_element.send_keys(Keys.DOWN)
        active_web_element.send_keys(Keys.ENTER)
        with self.assertRaises(ElementDoesNotExist) as context:
            selected = self.browser.find_by_xpath("//select[@id='id_termination_b_id']/option").first
        self.assertIn("no elements could be found", str(context.exception))

        # check the correct css query is present in the HTML
        js_query = (
            '"select#id_termination_b_region, select#id_termination_b_site, '
            'select#id_termination_b_rack, select#id_termination_b_device"'
        )
        self.assertIn(js_query, self.browser.html)
