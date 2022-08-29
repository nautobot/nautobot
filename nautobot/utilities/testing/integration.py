import os
import time

from celery.contrib.testing.worker import start_worker
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.test import tag
from django.urls import reverse
from django.utils.functional import classproperty
from selenium import webdriver
from splinter.browser import Browser

from nautobot.core.celery import app
from nautobot.utilities.testing.mixins import NautobotTestCaseMixin


# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "host.docker.internal")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


FIREFOX_PROFILE_PREFERENCES = {
    "network.http.pipelining": True,
    "network.http.proxy.pipelining": True,
    "network.http.pipelining.maxrequests": 8,
    "content.notify.interval": 500000,
    "content.notify.ontimer": True,
    "content.switch.threshold": 250000,
    "browser.cache.memory.capacity": 65536,  # Increase the cache capacity.
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
class SeleniumTestCase(StaticLiveServerTestCase, NautobotTestCaseMixin):
    """
    Base test case for Splinter Selenium integration testing with custom helper methods.

    This extends `django.contrib.staticfiles.testing.StaticLiveServerTestCase`
    so there is no need to run `collectstatic` prior to running tests.
    """

    host = "0.0.0.0"  # Always listen publicly
    selenium_host = SELENIUM_HOST  # Docker: `nautobot`; else `host.docker.internal`

    requires_celery = False  # If true, a celery instance will be started. TODO: create celery mixin?

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Instantiate the browser object.
        profile = cls._create_firefox_profile()
        cls.browser = Browser(
            "remote",
            command_executor=SELENIUM_URL,
            browser_profile=profile,
            # See: https://developer.mozilla.org/en-US/docs/Web/WebDriver/Timeouts
            # desired_capabilities={"timeouts": {"implicit": 60 * 60 * 1000 }},  # 1 hour timeout
        )

        if cls.requires_celery:
            app.loader.import_module("celery.contrib.testing.tasks")
            cls.clear_worker()
            cls.celery_worker = start_worker(app, concurrency=1)
            cls.celery_worker.__enter__()

    def setUp(self):
        super().setUpNautobot(populate_status=True)

        self.password = "testpassword"
        self.user.set_password(self.password)
        self.user.save()

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def live_server_url(cls):  # pylint: disable=no-self-argument
        return f"http://{cls.selenium_host}:{cls.server_thread.port}"

    @classmethod
    def tearDownClass(cls):
        """Close down the browser after tests are ran."""
        cls.browser.quit()
        if cls.requires_celery:
            cls.celery_worker.__exit__(None, None, None)

    def login(self, username, password, login_url=LOGIN_URL, button_text="Log In"):
        """
        Navigate to `login_url` and perform a login w/ the provided `username` and `password`.
        """
        self.browser.visit(f"{self.live_server_url}{login_url}")
        self.browser.fill("username", username)
        self.browser.fill("password", password)
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

    @staticmethod
    def clear_worker():
        """Purge any running or queued tasks"""
        app.control.purge()

    @classmethod
    def wait_on_active_tasks(cls):
        """Wait on all active tasks to finish before returning"""
        # TODO(john): admittedly, this is not great, but it seems the standard
        # celery APIs for inspecting the worker, looping through all active tasks,
        # and calling `.get()` on them is not working when the worker is in solo mode.
        # Needs more investigation and until then, these tasks run very quickly, so
        # simply delaying the test execution provides enough time for them to complete.
        time.sleep(1)
