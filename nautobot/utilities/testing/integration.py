import os

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.db.utils import IntegrityError
from django.test import Client, tag
from django.urls import reverse
from django.utils.functional import classproperty
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from splinter.browser import Browser

from nautobot.users.models import ObjectPermission
from nautobot.utilities.permissions import resolve_permission_ct


# Use the proper swappable User model
User = get_user_model()

# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "host.docker.internal")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


class NautobotRemote(webdriver.Remote):
    """Custom WebDriver with helpers."""

    def wait_for_html(self, tag_name, timeout=2):
        """Wait for the page to render and make sure we find `tag_name`."""
        WebDriverWait(self, timeout=timeout).until(lambda driver: driver.find_element_by_tag_name(tag_name))

    def find_button(self, button_text):
        """Return a `<button>` element with the given `button_text`."""
        return self.find_element_by_xpath(f'//button[text()="{button_text}"]')


FIREFOX_PROFILE_PREFERENCES = {
    "network.http.pipelining": True,
    "network.http.proxy.pipelining": True,
    "network.http.pipelining.maxrequests": 8,
    "content.notify.interval": 500000,
    "content.notify.ontimer": True,
    "content.switch.threshold": 250000,
    "browser.cache.memory.capacity": 65536,  # Increase the cache capacity.
    "browser.startup.homepage": "about:blank",
    "reader.parse-on-load.enabled": False,  # Disable reader: we won't need that.
    "browser.pocket.enabled": False,  # Firefox pocket too!
    "loop.enabled": False,
    "browser.chrome.toolbar_style": 1,  # Text on Toolbar instead of icons
    "browser.display.show_image_placeholders": False,  # Don't show thumbnails on not loaded images.
    "browser.display.use_document_colors": False,  # Don't show document colors.
    "browser.display.use_document_fonts": 0,  # Don't load document fonts.
    "browser.display.use_system_colors": True,  # Use system colors.
    "browser.formfill.enable": False,  # Autofill on forms disabled.
    "browser.helperApps.deleteTempFileOnExit": True,  # Delete temporary files.
    "browser.shell.checkDefaultBrowser": False,
    "browser.startup.homepage": "about:blank",
    "browser.startup.page": 0,  # Blank startup page
    "browser.tabs.forceHide": True,  # Disable tabs: We won't need that.
    "browser.urlbar.autoFill": False,  # Disable autofill on URL bar.
    "browser.urlbar.autocomplete.enabled": False,  # Disable autocomplete on URL bar.
    "browser.urlbar.showPopup": False,  # Disable list of URLs when typing on URL bar.
    "browser.urlbar.showSearch": False,  # Disable search bar.
    "extensions.checkCompatibility": False,  # Addon update disabled
    "extensions.checkUpdateSecurity": False,
    "extensions.update.autoUpdateEnabled": False,
    "extensions.update.enabled": False,
    "general.startup.browser": False,
    "plugin.default_plugin_disabled": False,
    "permissions.default.image": 2,
}


@tag("integration")
class SeleniumTestCase(StaticLiveServerTestCase):
    """
    Base test case for Selenium integration testing with custom helper methods.

    This extends `django.contrib.staticfiles.testing.StaticLiveServerTestCase`
    so there is no need to run `collectstatic` prior to running tests.
    """

    host = "0.0.0.0"  # Always listen publicly
    selenium_host = SELENIUM_HOST  # Docker: `nautobot`; else `host.docker.internal`
    user_permissions = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Selenium remote client
        cls.selenium = NautobotRemote(
            command_executor=SELENIUM_URL,
            options=cls._create_firefox_options(),
            browser_profile=cls._create_firefox_profile(),
        )

        # Wait for the DOM in case an element is not yet rendered.
        cls.selenium.implicitly_wait(10)

    def setUp(self):
        # Setup test user
        self.user, _ = User.objects.get_or_create(username="testuser")

        self.password = "testpassword"
        self.user.set_password(self.password)
        self.user.save()

    def add_permissions(self, *names):
        """
        Assign a set of permissions to the test user. Accepts permission names in the form <app>.<action>_<model>.
        """
        for name in names:
            ct, action = resolve_permission_ct(name)
            obj_perm = ObjectPermission(name=name, actions=[action])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ct)

    @classproperty
    def live_server_url(cls):
        return f"http://{cls.selenium_host}:{cls.server_thread.port}"

    @classmethod
    def tearDownClass(cls):
        """Close down the browser after tests are ran."""
        cls.selenium.quit()
        super().tearDownClass()

    def login(self, username, password, login_url=LOGIN_URL, button_text="Log In"):
        """
        Navigate to `login_url` and perform a login w/ the provided `username` and `password`.
        """

        self.selenium.get(f"{self.live_server_url}{login_url}")
        self.selenium.find_element_by_name("username").send_keys(username)
        self.selenium.find_element_by_name("password").send_keys(password)
        self.selenium.find_button(button_text).click()

        if "Please enter a correct username and password." in self.selenium.page_source:
            raise Exception(f"Unable to login in with username {username}")

    def logout(self):
        self.load_page(f"{self.live_server_url}/logout")

    def load_page(self, url):
        self.selenium.get(url)
        self.selenium.wait_for_html("body")

    @classmethod
    def _create_firefox_options(cls):
        """
        Return a `FirefoxOptions` with required arguments such as disabling the GPU and enabling
        headless mode.
        """

        options = webdriver.FirefoxOptions()
        options.headless = True
        options.add_argument("-disable-gpu")

        return options

    @classmethod
    def _create_firefox_profile(cls):
        """
        Return a `FirefoxProfile` with speed-optimized preferences such as disabling image loading,
        enabling HTTP pipelining, among others.

        Credit: https://bit.ly/2TuHa9D
        """

        profile = webdriver.FirefoxProfile()
        for key, value in FIREFOX_PROFILE_PREFERENCES.items():
            profile.set_preference(key, value)

        return profile


@tag("integration")
class SplinterTestCase(StaticLiveServerTestCase):
    """
    Base test case for Splinter Selenium integration testing with custom helper methods.

    This extends `django.contrib.staticfiles.testing.StaticLiveServerTestCase`
    so there is no need to run `collectstatic` prior to running tests.
    """

    host = "0.0.0.0"  # Always listen publicly
    selenium_host = SELENIUM_HOST  # Docker: `nautobot`; else `host.docker.internal`
    user_permissions = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Instantiate the browser object
        profile = cls._create_firefox_profile()
        cls.browser = Browser("remote", command_executor=SELENIUM_URL, browser_profile=profile)

    def setUp(self):
        # Setup test user
        self.user, _ = User.objects.get_or_create(username="testuser")

        self.password = "testpassword"
        self.user.set_password(self.password)
        self.user.save()

    def add_permissions(self, *names):
        """
        Assign a set of permissions to the test user. Accepts permission names in the form <app>.<action>_<model>.
        """
        for name in names:
            ct, action = resolve_permission_ct(name)
            obj_perm = ObjectPermission(name=name, actions=[action])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ct)

    @classproperty
    def live_server_url(cls):
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
        self.browser.fill("username", self.user.username)
        self.browser.fill("password", self.password)
        self.browser.find_by_xpath(f"//button[text()='{button_text}']").first.click()

        if self.browser.is_text_present("Please enter a correct username and password."):
            raise Exception(f"Unable to login in with username {username}")

    def logout(self):
        self.browser.visit(f"{self.live_server_url}/logout")

    @classmethod
    def _create_firefox_profile(cls):
        """
        Return a `FirefoxProfile` with speed-optimized preferences such as disabling image loading,
        enabling HTTP pipelining, among others.

        Credit: https://bit.ly/2TuHa9D
        """

        profile = webdriver.FirefoxProfile()
        for key, value in FIREFOX_PROFILE_PREFERENCES.items():
            profile.set_preference(key, value)

        return profile
