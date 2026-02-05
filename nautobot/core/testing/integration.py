import os
from typing import Any, Optional

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Model
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.functional import classproperty
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import element_to_be_clickable
from selenium.webdriver.support.wait import WebDriverWait
from splinter.browser import Browser
from splinter.exceptions import ElementDoesNotExist

from nautobot.core import testing

# URL used to connect to the Selenium host
SELENIUM_URL = os.getenv("NAUTOBOT_SELENIUM_URL", "http://localhost:4444/wd/hub")

# Hostname used by Selenium client to talk to Nautobot
SELENIUM_HOST = os.getenv("NAUTOBOT_SELENIUM_HOST", "nautobot")

# Default login URL
LOGIN_URL = reverse(settings.LOGIN_URL)


class ObjectsListMixin:
    """
    Helper class for easier testing and navigating on standard Nautobot objects list page.
    """

    def select_all_items(self):
        """
        Click "toggle all" on top of the items table list to select all rows.
        """
        self.browser.find_by_css("#object_list_form input.toggle").click()

    def select_one_item(self, pk=None):
        """
        Click first row checkbox on items table list to select one row.
        """
        selector = '#object_list_form input[name="pk"]'
        if pk:
            selector = f'{selector}[value="{pk}"]'

        self.browser.find_by_css(selector).click()

    def set_per_page(self, per_page=1):
        """
        Explicitly set the `per_page` parameter by navigating to the "current" page but with query param.
        TODO: check if there are other query params and merge them
        """
        self.browser.visit(f"{self.browser.url}?per_page={per_page}")

    def select_all_items_from_all_pages(self):
        """
        Selecting all the items from all pages by clicking "select all" on top of the items table list and then
        select all on prompt that will show up.
        """
        self.select_all_items()
        self.browser.find_by_css("#select_all").click()

    def click_bulk_delete(self):
        """
        Click bulk delete from dropdown menu on bottom of the items table list.
        """
        self.scroll_element_into_view(css='#bulk-action-buttons button[type="submit"]')
        self.browser.find_by_xpath(
            '//*[@id="bulk-action-buttons"]//button[@type="submit"]/following-sibling::button[1]'
        ).click()
        bulk_delete_button = self.browser.find_by_css('#bulk-action-buttons button[name="_delete"]')
        bulk_delete_button.is_visible(wait_time=5)
        self.scroll_element_into_view(element=bulk_delete_button)
        bulk_delete_button.click()

    def click_bulk_delete_all(self):
        """
        Click bulk delete all on prompt when selecting all items from all pages.
        """
        self.click_button('#select_all_box button[name="_delete"]')

    def click_bulk_edit(self):
        """
        Click bulk edit button on bottom of the items table list.
        """
        self.click_button('#bulk-action-buttons button[type="submit"]')

    def click_bulk_edit_all(self):
        """
        Click bulk edit all on prompt when selecting all items from all pages.
        """
        self.click_button('#select_all_box button[name="_edit"]')

    def click_add_item(self):
        """
        Click add item button on top of the items table list.
        """
        self.click_button("#add-button")

    def click_table_link(self, row=1, column=2):
        """By default, tries to click column next to checkbox to go to the details page."""
        self.browser.find_by_xpath(f'//*[@id="object_list_form"]//tbody/tr[{row}]/td[{column}]/a').click()

    @property
    def objects_list_visible_items(self):
        """
        Calculating the visible items. Return 0 if there is no visible items.
        """
        objects_table_container = self.browser.find_by_xpath('//*[@id="object_list_form"]')
        try:
            objects_table = objects_table_container.find_by_tag("tbody")
            return len(objects_table.find_by_xpath(".//tr[not(count(td[@colspan])=1)]"))
        except ElementDoesNotExist:
            return 0

    def apply_filter(self, field, value):
        """
        Open filter dialog and apply select2 filters.
        You can apply more values to the same filter, by calling this function with same name but different value.
        """
        self.browser.find_by_xpath('//*[@id="id__filterbtn"]').click()
        self.fill_filters_select2_field(field, value)
        self.click_button('#default-filter button[type="submit"]')


class ObjectDetailsMixin:
    def assertPanelValue(self, panel_label, field_label, expected_value, exact_match=False):
        """
        Find the proper panel and asserts if given value match rendered field value.
        By default, it's not using the exact match, because on the UI we're often adding
        additional tags, relationships or units.
        """
        panel_xpath = f'//*[@id="main"]//div[contains(@class, "card-header") and contains(normalize-space(), "{panel_label}")]/following-sibling::div[contains(@class, "collapse")]/table'
        value = self.browser.find_by_xpath(f'{panel_xpath}//td[text()="{field_label}"]/following-sibling::td[1]').text

        if exact_match:
            self.assertEqual(value, str(expected_value))
        else:
            self.assertIn(str(expected_value), value)

    def find_and_open_panel_v2(self, panel_label):
        """
        Finds panel with given title and expand it if needed. Works with v2 template panels.

        TODO: remove after all panels will be moved to UI Components Framework or new Bootstrap 5 templates.
        """
        panel_xpath = f'//*[@id="main"]//div[@class="card-header"][contains(normalize-space(), "{panel_label}")]'
        expand_button_xpath = f"{panel_xpath}/button[normalize-space()='Expand All Groups']"
        expand_button = self.browser.find_by_xpath(expand_button_xpath)
        if not expand_button.is_empty():
            expand_button.click()
        return self.browser.find_by_xpath(f"{panel_xpath}/../table")

    def switch_tab(self, tab_name):
        """Finds and click tab based on tab name from the tab link."""
        self.get_tab_link(tab_name).click()

    def get_tab_link(self, tab_name):
        """
        Finds tab link either in dropdown menu, cloned menu or standard tabs list
        depending on the browser size and tabs count.

        Please note, that if tab will be placed in dropdown menu this function will left this menu open.
        """
        tabs_container_xpath = '//div[@data-nb-tests-id="object-details-header-tabs"]'
        toggle_button_xpath = f'{tabs_container_xpath}//button[@data-bs-toggle="dropdown"]'
        toggle_button = self.browser.find_by_xpath(toggle_button_xpath, wait_time=5)
        if toggle_button:
            # Our tab might be hidden
            tab_xpath = (
                f'{tabs_container_xpath}//ul[@data-clone="true"]/li/a[contains(normalize-space(), "{tab_name}")]'
            )
            visible_tab = self.browser.find_by_xpath(tab_xpath, wait_time=5)
            if visible_tab:
                return visible_tab

            # If hidden, click toggle to show the dropdown menu
            toggle_button.click()
            tab_xpath = f'{toggle_button_xpath}/following-sibling::ul//a[contains(normalize-space(), "{tab_name}")]'
            return self.browser.find_by_xpath(tab_xpath, wait_time=5)

        tab_xpath = (
            f'//ul[@data-nb-tests-id="object-details-header-tabs-ul"]//a[contains(normalize-space(), "{tab_name}")]'
        )
        return self.browser.find_by_xpath(tab_xpath, wait_time=5)


class BulkOperationsMixin:
    def confirm_bulk_delete_operation(self):
        """
        Confirms bulk delete operation on the "warning" page after clicking bulk delete buttons.
        """
        self.click_button('button[name="_confirm"][type="submit"]')

    def submit_bulk_edit_operation(self):
        """
        Submits the bulk edit form.
        """
        self.click_button('button[name="_apply"]')

    def wait_for_job_result(self):
        """
        Waits 30s for job to be finished.
        """
        end_statuses = ["Completed", "Failed"]
        WebDriverWait(self.browser, 30).until(
            lambda driver: driver.find_by_id("pending-result-label").text in end_statuses
        )

        return self.browser.find_by_id("pending-result-label").text

    def verify_job_description(self, expected_job_description):
        """
        Verifies if the job description is correct.
        Waits 30s on page load in case of large payload being sent from bulk edit form.
        """
        WebDriverWait(self.browser, 30).until(lambda driver: driver.is_text_present("Job Description"))

        job_description = self.browser.find_by_xpath('//td[text()="Job Description"]/following-sibling::td[1]').text
        self.assertEqual(job_description, expected_job_description)

    def update_edit_form_value(self, field_name, value, is_select=False):
        """
        Updates bulk edit form value.
        """
        if is_select:
            self.fill_select2_field(field_name, value)
        else:
            self.fill_input(field_name, value)

    def assertBulkDeleteConfirmMessageIsValid(self, expected_count):
        """
        Asserts that bulk delete confirmation message is valid and if we're deleting proper number of items.
        """
        self.browser.is_element_present_by_tag("body", wait_time=30)

        button_text = self.browser.find_by_xpath('//button[@name="_confirm" and @type="submit"]').text
        self.assertIn(f"Delete these {expected_count}", button_text)

        message_text = self.browser.find_by_id("confirm-bulk-deletion").find_by_xpath('//div[@class="card-body"]').text
        self.assertIn(f"The following operation will delete {expected_count}", message_text)

    def assertIsBulkDeleteJob(self):
        """
        Asserts if currently visible job is bulk delete job.
        """
        self.verify_job_description("Bulk delete objects.")

    def assertIsBulkEditJob(self):
        """
        Asserts if currently visible job is bulk edit job.
        """
        self.verify_job_description("Bulk edit objects.")

    def assertJobStatusIsCompleted(self):
        """
        Asserts that job was successfully completed.
        """
        job_status = self.wait_for_job_result()
        self.assertEqual(job_status, "Completed")


class SidenavSection:
    """
    Helper class which represents a Sidenav section and simplify moving around sidenav, expanding section and clicking
    proper navigation link.
    """

    def __init__(self, browser, section_name):
        self.browser = browser
        self.section_name = section_name
        self.section_xpath = f"//*[@id='sidenav']//li[@data-section-name='{self.section_name}']"
        self.section = self.browser.find_by_xpath(self.section_xpath)

    @property
    def button(self):
        return self.section.find_by_xpath(f"{self.section_xpath}/button")

    @property
    def flyout(self):
        return self.section.find_by_xpath(f"{self.section_xpath}/div[@class='nb-sidenav-flyout']")

    @property
    def is_expanded(self):
        return self.button["aria-expanded"] == "true"

    def toggle(self):
        if not self.is_expanded:
            self.button.click()

    def find_link(self, link_name):
        return self.section.find_by_xpath(
            f"{self.section_xpath}/div[@class='nb-sidenav-flyout']//a[@class='nb-sidenav-link' and normalize-space()='{link_name}']"
        )

    def click_link(self, link_name):
        link = self.find_link(link_name)
        link.click()


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
    logged_in = False

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

    def tearDown(self):
        if self.logged_in:
            self.logout()

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

        self.logged_in = True

    def logout(self):
        self.browser.visit(f"{self.live_server_url}/logout")

    def find_sidenav_section(self, tab_name):
        """
        Helper function to find sidenav section known as "tab_name". In `nav_menu` we still have tabs/groups naming.
        """
        return SidenavSection(self.browser, tab_name)

    def click_navbar_entry(self, parent_menu_name, child_menu_name):
        """
        Helper function to click on a parent menu and child menu in the navigation bar.
        """
        section_xpath = f"//*[@id='sidenav']//li[@data-section-name='{parent_menu_name}']"
        sidenav_button = self.browser.find_by_xpath(f"{section_xpath}/button", wait_time=5)
        if not sidenav_button["aria-expanded"] == "true":
            sidenav_button.click()
        child_menu_xpath = f"{section_xpath}/div[@class='nb-sidenav-flyout']//a[contains(@class, 'nb-sidenav-link') and normalize-space()='{child_menu_name}']"
        child_menu = self.browser.find_by_xpath(child_menu_xpath, wait_time=5)
        old_url = self.browser.url
        child_menu.click()

        WebDriverWait(self.browser, 30).until(lambda driver: driver.url != old_url)
        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def click_list_view_add_button(self):
        """
        Helper function to click the "Add" button on a list view.
        """
        add_button = self.browser.find_by_xpath("//a[@id='add-button']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_name("_create", wait_time=5), "Page failed to load")

    def click_edit_form_create_button(self):
        """
        Helper function to click the "Create" button on a form.
        """
        add_button = self.browser.find_by_xpath("//button[@name='_create']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_css(".alert-success", wait_time=5), "Page failed to load")

    def _fill_select2_field(self, field_name, value, search_box_class=None):
        """
        Helper function to fill a Select2 single selection field.
        """
        if search_box_class is None:
            search_box_class = "select2-search select2-search--dropdown"

        self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span").click()
        self.scroll_element_into_view(css=f"#id_{field_name}")
        search_box = self.browser.find_by_xpath(f"//*[@class='{search_box_class}']//input", wait_time=5)
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        return search_box

    def _select_select2_result(self):
        found_results = self.browser.find_by_css(".select2-results li.select2-results__option")
        # click the first found item if it's not `None`: special value to nullify field
        if found_results.first.text != "None":
            found_results.first.click()
        else:
            found_results[1].click()

    def fill_select2_field(self, field_name, value):
        """
        Helper function to fill a Select2 single selection field on add/edit forms.
        """
        self._fill_select2_field(field_name, value)
        self._select_select2_result()

    def fill_filters_select2_field(self, field_name, value):
        """
        Helper function to fill a Select2 single selection field on filters modals.
        """
        self._fill_select2_field(field_name, value, search_box_class="select2-search select2-search--inline")
        self._select_select2_result()

    def fill_select2_multiselect_field(self, field_name, value):
        """
        Helper function to fill a Select2 multi-selection field.
        """
        search_box = self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span//input")
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        search_box.first.type(Keys.ENTER)

    def click_button(self, query_selector):
        self.browser.is_element_present_by_css(query_selector, wait_time=5)
        # Button might be visible but on the edge and then impossible to click due to vertical/horizontal scrolls
        self.scroll_element_into_view(css=query_selector)
        # Scrolling may be asynchronous, wait until it's actually clickable.
        WebDriverWait(self.browser.driver, 30).until(element_to_be_clickable((By.CSS_SELECTOR, query_selector)))
        btn = self.browser.find_by_css(query_selector)
        btn.click()

    def fill_input(self, input_name, input_value):
        """
        Helper function to fill an input field. Solves issue with element could not be scrolled into view for some pages.
        """
        self.browser.is_element_present_by_name(input_name, wait_time=5)
        element = self.browser.find_by_name(input_name)
        self.scroll_element_into_view(element=element)
        element.is_visible(wait_time=5)
        self.browser.execute_script("arguments[0].focus();", element.first._element)
        self.browser.fill(input_name, input_value)

    def login_as_superuser(self):
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        self.logged_in = True

    def scroll_element_into_view(self, element=None, css=None, xpath=None, block="start"):
        """
        Scroll element into view. Element can be expressed either as Splinter `ElementList`, `ElementAPI`, CSS query selector or XPath.
        """
        if css:
            element = self.browser.find_by_css(css)
        elif xpath:
            element = self.browser.find_by_xpath(xpath)

        self.browser.execute_script(
            f"arguments[0].scrollIntoView({{ behavior: 'instant', block: '{block}' }});",
            element.first._element if hasattr(element, "__iter__") else element._element,
        )


class BulkOperationsTestCases:
    """
    Helper classes that runs all the basic bulk-operations test cases like edit/delete with
    filtered / not filtered items along with select all option.

    To use this class create required items in setUp method:
    - at least four entities in two different groups,
    - provide field for filtering to distinguish between above two groups
    - provide expected counts (if different from default)
    - set edit field and value
    """

    class BaseTestCase(SeleniumTestCase):
        model_menu_path: tuple[str, str]
        model_base_viewname: str
        model_edit_data: dict[str, Any]
        model_filter_by: dict[str, Any]
        model_class: type[Model]
        override_model_plural: Optional[str] = None
        model_expected_counts: dict[str, int] = {
            "all": 5,
            "filtered": 2,
        }

        @property
        def model_plural(self) -> str:
            if self.override_model_plural is None:
                return self.model_class._meta.verbose_name_plural

            return self.override_model_plural

        def setUp(self):
            super().setUp()

            self.setup_items()
            self.login_as_superuser()
            self.go_to_model_list_page()

        def go_to_model_list_page(self):
            self.click_navbar_entry(*self.model_menu_path)
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))

        def setup_items(self):
            raise NotImplementedError

    class BulkEditTestCase(BaseTestCase, ObjectsListMixin, BulkOperationsMixin):
        def test_bulk_edit_require_selection(self):
            # Click "edit selected" without selecting anything
            self.click_bulk_edit()

            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))
            self.assertTrue(self.browser.is_text_present(f"No {self.model_plural} were selected", wait_time=5))

        def test_bulk_edit_all_items(self):
            # Select all items and edit them
            self.select_all_items()
            self.click_bulk_edit()
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"))

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["all"])

        def test_bulk_edit_one_item(self):
            # Select one filtered item
            self.select_one_item()
            self.click_bulk_edit()
            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"))

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, 1)

        def test_bulk_edit_all_items_from_all_pages(self):
            # Select all from all pages
            self.set_per_page()
            self.select_all_items_from_all_pages()
            self.click_bulk_edit_all()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["all"])

        def test_bulk_edit_all_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all filtered items
            self.select_all_items()
            self.click_bulk_edit()
            self.assertIn(
                self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"),
                self.browser.url,
            )

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["filtered"])

        def test_bulk_edit_one_filtered_item(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select one item and edit it
            self.select_one_item()
            self.click_bulk_edit()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, 1)

        def test_bulk_edit_all_filtered_items_from_all_pages(self):
            # Filter items
            self.set_per_page()
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items_from_all_pages()
            self.click_bulk_edit_all()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_edit"), self.browser.url)

            # Edit some data and submit the form
            for field_name, field_value in self.model_edit_data.items():
                self.update_edit_form_value(field_name, field_value)
            self.submit_bulk_edit_operation()

            # Verify job output
            self.assertIsBulkEditJob()
            self.assertJobStatusIsCompleted()

            # Assert that data was changed
            found_items = self.model_class.objects.filter(**self.model_edit_data).count()
            self.assertEqual(found_items, self.model_expected_counts["filtered"])

    class BulkDeleteTestCase(BaseTestCase, ObjectsListMixin, BulkOperationsMixin):
        def test_bulk_delete_require_selection(self):
            # Click "delete selected" without selecting anything
            self.click_bulk_delete()

            self.assertEqual(self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_list"))
            self.assertTrue(
                self.browser.is_text_present(f"No {self.model_plural} were selected for deletion.", wait_time=5)
            )

        def test_bulk_delete_all_items(self):
            # Select all items and delete them
            self.select_all_items()
            self.click_bulk_delete()

            self.assertEqual(
                self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete")
            )
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["all"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, 0)

        def test_bulk_delete_one_item(self):
            # Select one item and delete it
            self.select_one_item()
            self.click_bulk_delete()

            self.assertEqual(
                self.browser.url, self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete")
            )
            self.assertBulkDeleteConfirmMessageIsValid(1)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, self.model_expected_counts["all"] - 1)

        def test_bulk_delete_all_items_from_all_pages(self):
            # Select all from all pages
            self.set_per_page()
            self.select_all_items_from_all_pages()
            self.click_bulk_delete_all()

            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["all"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, 0)

        def test_bulk_delete_all_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items()
            self.click_bulk_delete()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            # We set page size to large number to avoid pagination issues
            self.set_per_page(1000)
            rest_items_count = self.model_expected_counts["all"] - self.model_expected_counts["filtered"]
            self.assertEqual(self.objects_list_visible_items, rest_items_count)

        def test_bulk_delete_one_filtered_items(self):
            # Filter items
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select one item and delete it
            self.select_one_item()
            self.click_bulk_delete()
            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.assertEqual(self.objects_list_visible_items, self.model_expected_counts["all"] - 1)

        def test_bulk_delete_all_filtered_items_from_all_pages(self):
            # Filter items
            self.set_per_page()
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)

            # Select all items and delete them
            self.select_all_items_from_all_pages()
            self.click_bulk_delete_all()

            self.assertIn(self.live_server_url + reverse(f"{self.model_base_viewname}_bulk_delete"), self.browser.url)
            self.assertBulkDeleteConfirmMessageIsValid(self.model_expected_counts["filtered"])
            self.confirm_bulk_delete_operation()

            # Verify job output
            self.assertIsBulkDeleteJob()
            self.assertJobStatusIsCompleted()

            self.go_to_model_list_page()
            self.set_per_page(50)  # Set page size back to default
            rest_items_count = self.model_expected_counts["all"] - self.model_expected_counts["filtered"]
            self.assertEqual(self.objects_list_visible_items, rest_items_count)

            # Filter again and assert that all items were deleted
            for field, value in self.model_filter_by.items():
                self.apply_filter(field, value)
            self.assertEqual(self.objects_list_visible_items, 0)

    class BulkOperationsTestCase(BulkEditTestCase, BulkDeleteTestCase):
        pass
