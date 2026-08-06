from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from nautobot.core.testing.integration import SeleniumTestCase


class JobListCollapseAndExpandButton(SeleniumTestCase):
    """Integration tests for the Jobs List page's Collapse/Expand All Button"""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _wait_until(self, time_in_seconds, condition):
        WebDriverWait(self.browser.driver, time_in_seconds, poll_frequency=0.1).until(lambda _driver: condition())

    def _visit_job_list(self):
        self.browser.visit(f"{self.live_server_url}/extras/jobs/")
        self._wait_until(2, lambda: self._get_total_row_count() > 0)

    def _visit_job_list_page(self, page_number):
        page_input = self.browser.find_by_id("paginator-go-to", wait_time=2).first
        self.scroll_element_into_view(element=page_input)
        page_input.fill(str(page_number))
        page_input.type(Keys.RETURN)
        self._wait_until(2, lambda: f"page={page_number}" in self.browser.url)

    def _get_job_group_count(self):
        return self.browser.driver.execute_script(
            "return new Set([...document.querySelectorAll('#job_accordion .collapse')]"
            ".map((el) => [...el.classList].find((cls) => cls.startsWith('collapseme-')))).size"
        )

    def _get_collapsed_row_count(self):
        return self.browser.driver.execute_script(
            "return [...document.querySelectorAll('#job_accordion .collapse')]"
            ".filter((el) => window.getComputedStyle(el).display === 'none').length"
        )

    def _get_expanded_row_count(self):
        return self.browser.driver.execute_script(
            "return document.querySelectorAll('#job_accordion .collapse.show').length"
        )

    def _get_total_row_count(self):
        return self.browser.driver.execute_script("return document.querySelectorAll('#job_accordion .collapse').length")

    def _get_collapse_all_button_text(self):
        return self.browser.find_by_css('[data-nb-toggle="collapse-all"]').first.text

    def _get_job_list_page_count(self):
        if not self.browser.is_element_present_by_id("paginator-go-to"):
            return 1
        return int(self.browser.find_by_id("paginator-go-to").first["max"])

    def _click_collapse_all_button(self):
        button = self.browser.find_by_css('[data-nb-toggle="collapse-all"]', wait_time=2).first
        self.scroll_element_into_view(element=button)
        button.click()

    def _click_expand_all_button(self):
        self._wait_until(2, lambda: self._get_collapse_all_button_text() == "Expand All Groups")
        self._click_collapse_all_button()

    def _expand_first_group(self):
        expansion_indicator = self.browser.find_by_css('#job_accordion [data-bs-toggle="collapse"]', wait_time=2).first
        self.scroll_element_into_view(element=expansion_indicator)
        expansion_indicator.click()

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_default_job_list_is_fully_expanded(self):
        """Default Job List should show all jobs expanded"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_default_collapse_all_button_text_is_collapse_all_groups(self):
        """Default state is fully expanded job list, so collapse all button should say 'Collapse All Groups'"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

    def test_collapse_all_button_collapses_all(self):
        """Collapse All Button must collapse every job group"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_expand_all_button_expands_all(self):
        """Expand All Button must expand every job group"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())
        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_button_changes_text_to_expand_all_groups_string_after_all_jobs_are_collapsed(self):
        """Collapse All Button text must say 'Expand All Groups' when all jobs are collapsed"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        # Collapse 'em all down
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        # Check button
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

    def test_collapse_all_groups_persist_after_revisit_to_page(self):
        """Collapse State must persist after page reload"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

        self.browser.reload()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_persists_across_job_list_pages(self):
        """Collapsing all job groups must stay collapsed when paginating to another page and back"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreater(self._get_job_list_page_count(), 1)

        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self._visit_job_list_page(2)

        self._visit_job_list_page(1)
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_collapse_all_from_mixed_state_collapses_every_group(self):
        """Collapse All must collapse every group even when a reload restores a mixed state"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreaterEqual(self._get_job_group_count(), 2)

        self._click_collapse_all_button()
        self._expand_first_group()

        self.browser.reload()

        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_collapse_all_on_a_later_page_collapses_earlier_pages(self):
        """Collapsing all groups while on page two must also collapse page one when navigating back"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreater(self._get_job_list_page_count(), 1)

        self._visit_job_list_page(2)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

        self._visit_job_list_page(1)
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_collapse_all_on_page_two_keeps_untouched_page_one_groups_collapsed(self):
        """Collapse-All on page two, then reopening that page's group, must leave page one's other groups collapsed"""
        self._visit_job_list()
        self.browser.driver.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreater(self._get_job_list_page_count(), 1)

        self._visit_job_list_page(2)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

        self._expand_first_group()
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

        self._visit_job_list_page(1)
        self.assertGreater(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")
