from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import CollapseAllButtonTestCase


class JobListCollapseAndExpandButton(CollapseAllButtonTestCase):
    """Integration tests for the Jobs List page's Collapse/Expand All Button"""

    TOGGLE_ALL_BUTTON_SELECTOR = '[data-nb-toggle="collapse-all"]'
    GROUP_ROW_SELECTOR = "#job_accordion .collapse"
    GROUP_TOGGLE_SELECTOR = '#job_accordion [data-bs-toggle="collapse"]'

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _visit_job_list(self):
        self.browser.visit(f"{self.live_server_url}/extras/jobs/")
        self.browser.is_element_present_by_css(self.GROUP_ROW_SELECTOR, wait_time=2)

    def _visit_job_list_page(self, page_number):
        page_input = self.browser.find_by_id("paginator-go-to", wait_time=2).first
        self.scroll_element_into_view(element=page_input)
        page_input.fill(str(page_number))
        page_input.type(Keys.RETURN)
        self.browser.is_element_present_by_xpath(
            f'//li[contains(@class, "page-item") and contains(@class, "active")]//a[normalize-space() = "{page_number}"]',
            wait_time=2,
        )

    def _get_job_list_page_count(self):
        if not self.browser.is_element_present_by_id("paginator-go-to"):
            return 1
        return int(self.browser.find_by_id("paginator-go-to").first["max"])

    # --------------------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------------------
    def test_default_job_list_is_fully_expanded(self):
        """Default Job List should show all jobs expanded"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_default_collapse_all_button_text_is_collapse_all_groups(self):
        """Default state is fully expanded job list, so collapse all button should say 'Collapse All Groups'"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

    def test_collapse_all_button_collapses_all(self):
        """Collapse All Button must collapse every job group"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_expand_all_button_expands_all(self):
        """Expand All Button must expand every job group"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertEqual(self._get_collapsed_row_count(), 0)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())
        self._click_expand_all_button()
        self.assertEqual(self._get_expanded_row_count(), self._get_total_row_count())

    def test_collapse_all_button_changes_text_to_expand_all_groups_string_after_all_jobs_are_collapsed(self):
        """Collapse All Button text must say 'Expand All Groups' when all jobs are collapsed"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
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
        self.browser.execute_script("window.localStorage.clear();")
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
        self.browser.execute_script("window.localStorage.clear();")
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
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreaterEqual(self._get_group_count(), 2)

        self._click_collapse_all_button()
        self._expand_first_group()

        # Wait for the reopened group to render and persist before reloading, so the reload restores the intended mixed state rather than a uniform one.
        self.browser.is_element_present_by_css(f"{self.GROUP_ROW_SELECTOR}.show", wait_time=2)
        self.assertGreater(self._get_collapsed_row_count(), 0)

        self.browser.reload()
        self.assertGreater(self._get_expanded_row_count(), 0)

        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())

    def test_collapse_all_on_a_later_page_collapses_earlier_pages(self):
        """Collapsing all groups while on page two must also collapse page one when navigating back"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
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
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreater(self._get_job_list_page_count(), 1)

        self._visit_job_list_page(2)
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

        self._expand_first_group()
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

        self._visit_job_list_page(1)
        self.assertGreater(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

    def test_collapse_all_button_text_only_flips_when_every_group_matches(self):
        """The button label persists through mixed states, flipping only once every group is collapsed or expanded"""
        self._visit_job_list()
        self.browser.execute_script("window.localStorage.clear();")
        self.browser.reload()

        self.assertGreaterEqual(self._get_group_count(), 2)

        # Every group expanded: the button offers to collapse.
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

        # Collapsing a single group leaves a mixed state, so the label must not flip yet.
        self._expand_first_group()
        self.assertGreater(self._get_collapsed_row_count(), 0)
        self.assertGreater(self._get_expanded_row_count(), 0)
        self.assertEqual(self._get_collapse_all_button_text(), "Collapse All Groups")

        # Once every group is collapsed, the label flips to offer expand.
        self._click_collapse_all_button()
        self.assertEqual(self._get_collapsed_row_count(), self._get_total_row_count())
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")

        # Expanding a single group leaves a mixed state again, so the label must not flip back yet.
        self._expand_first_group()
        self.assertGreater(self._get_expanded_row_count(), 0)
        self.assertGreater(self._get_collapsed_row_count(), 0)
        self.assertEqual(self._get_collapse_all_button_text(), "Expand All Groups")
