import os

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.functional import classproperty
from splinter.browser import Browser

from nautobot.core import testing

# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "host.docker.internal")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


# In CI, sometimes the FQDN of SELENIUM_HOST gets used, other times it seems to be just the hostname?
@override_settings(ALLOWED_HOSTS=["nautobot.example.com", SELENIUM_HOST, SELENIUM_HOST.split(".")[0]])
@tag("integration")
class SeleniumTestCase(StaticLiveServerTestCase, testing.NautobotTestCaseMixin):
    """
    Base test case for Splinter Selenium integration testing with custom helper methods.

    This extends `django.contrib.staticfiles.testing.StaticLiveServerTestCase`
    so there is no need to run `collectstatic` prior to running tests.
    """

    host = "0.0.0.0"  # noqa: S104  # hardcoded-bind-all-interfaces -- false positive
    selenium_host = SELENIUM_HOST  # Docker: `nautobot`; else `host.docker.internal`

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Instantiate the browser object.
        cls.browser = Browser(
            "remote",
            command_executor=SELENIUM_URL,
            # See: https://developer.mozilla.org/en-US/docs/Web/WebDriver/Timeouts
            # desired_capabilities={"timeouts": {"implicit": 60 * 60 * 1000 }},  # 1 hour timeout
        )

    def setUp(self):
        super().setUpNautobot(populate_status=True)

        self.password = "testpassword"  # noqa: S105  # hardcoded-password-string
        self.user.set_password(self.password)
        self.user.save()

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def live_server_url(cls):  # pylint: disable=no-self-argument
        return f"http://{cls.selenium_host}:{cls.server_thread.port}"

    @classmethod
    def tearDownClass(cls):
        """Close down the browser after tests are ran."""
        cls.browser.quit()

    def login(self, username, password, login_url=LOGIN_URL, button_text="Log In"):
        """
        Navigate to `login_url` and perform a login w/ the provided `username` and `password`.
        """
        self.browser.visit(f"{self.live_server_url}{login_url}")
        self.browser.fill("username", username)
        self.browser.fill("password", password)
        self.browser.find_by_xpath(f"//button[text()='{button_text}']").first.click()

        if self.browser.is_text_present("Please enter a correct username and password."):
            self.fail(f"Unable to login in with username {username}")

    def logout(self):
        self.browser.visit(f"{self.live_server_url}/logout")
