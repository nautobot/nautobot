import logging
import os
from unittest import skipIf

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait


# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")
logging.debug("SELENIUM_URL = %s", SELENIUM_URL)

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "localhost")
logging.debug("SELENIUM_HOST = %s", SELENIUM_HOST)


@skipIf(
    "NAUTOBOT_INTEGRATION_TEST" not in os.environ,
    "NAUTOBOT_INTEGRATION_TEST environment variable not set",
)
class MySeleniumTests(StaticLiveServerTestCase):
    host = SELENIUM_HOST  # Docker: `nautobot`; else `localhost`
    fixtures = ["user-data.json"]  # bob/bob

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Firefox driver
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.headless = True
        # firefox_options.add_argument("-headless")
        # firefox_options.add_argument("--screenshot")
        # firefox_options.add_argument("--no-sandbox")
        # firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("-disable-gpu")

        # Selenium remote client
        cls.selenium = webdriver.Remote(
            command_executor=SELENIUM_URL,
            options=firefox_options,
        )

        # Wait for the DOM in case an element is not yet rendered.
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self):
        self.selenium.get("%s%s" % (self.live_server_url, "/login/"))
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys("bob")
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys("bob")
        self.selenium.find_element_by_xpath('//button[text()="Log In"]').click()

        # Wait for the page to render and make sure we got a body.
        WebDriverWait(self.selenium, timeout=2).until(lambda driver: driver.find_element_by_tag_name("body"))
        # self.selenium.find_element_by_xpath('//div[text()="Logged in as "]').click()
