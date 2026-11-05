import time
from unittest import skip

from django.utils import timezone
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models.jobs import Job, JobLogEntry, JobResult


class JobResultTest(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    @skip("Test fails currently because of a bug with Selenium Mozila Browser not registering events on time")
    def test_log_table_filter(self):
        """
        Create fake job log entries for testing the log filtering.
        """

        # Set required job variables
        job = Job.objects.get(name="Example logging job.")
        job.has_sensitive_variables = False
        job.enabled = True
        job.save()

        # Create fake job result
        job_result = JobResult.objects.create(
            job_model=job,
            name=job.class_path,
            user=self.user,
            status=JobResultStatusChoices.STATUS_STARTED,
        )
        job_result.save()

        # Create fake log entries
        log_entries = []
        for i, log_level in enumerate(LogLevelChoices.values()):
            log_entries.append(
                JobLogEntry.objects.create(
                    log_level=log_level,
                    grouping="run",
                    job_result=job_result,
                    message=f"Log {i + 1}",
                )
            )

        # Complete the job
        job_result.date_done = timezone.now()
        job_result.status = JobResultStatusChoices.STATUS_SUCCESS
        job_result.save()

        # Visit the job result page
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("Jobs").first.click()
        self.browser.links.find_by_partial_text("Job Results").first.click()
        self.browser.find_by_xpath("//table[@class='table table-hover nb-table-headings']/tbody/tr[1]/td[2]/a").click()

        filter_element = self.browser.find_by_xpath("//input[@id='log-filter']")
        visible_rows_xpath = "//table[@id='logs']/tbody/tr[not(contains(@style, 'display: none'))]"

        def visible_rows():
            return self.browser.find_by_xpath(visible_rows_xpath)

        def get_cell_value(row, column):
            return self.browser.find_by_xpath(f"{visible_rows_xpath}[{row}]/td[{column}]").text

        log_level_column = 3
        message_column = 5

        # Sanity check
        self.assertEqual(len(LogLevelChoices.values()), len(visible_rows()))

        # Give selenium some time to attach event listeners
        time.sleep(10)

        # Test for message (one row should be visible)
        filter_element.fill("")
        filter_element.type(log_entries[0].message)
        self.browser.execute_script("document.querySelector('input#log-filter').dispatchEvent(new Event('input'));")

        self.browser.is_text_not_present(log_entries[3].message, 10)  # Wait for API call to return a response
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual(log_entries[0].log_level.title(), get_cell_value(1, log_level_column))
        self.assertEqual(log_entries[0].message, get_cell_value(1, message_column))

        # Test for log level (one row should be visible)
        filter_element.fill("")
        filter_element.type(log_entries[3].log_level.title())
        self.browser.execute_script("document.querySelector('input#log-filter').dispatchEvent(new Event('input'));")
        self.browser.is_text_not_present(log_entries[2].log_level.title(), 10)  # Wait for API call to return a response
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual(log_entries[3].log_level.title(), get_cell_value(1, log_level_column))
        self.assertEqual(log_entries[3].message, get_cell_value(1, message_column))

        # Test hitting return while the filter input is focused doesn't submit the form (producing a 405)
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        self.assertTrue(self.browser.is_text_present("Job Result"))

    def test_active_tabs_and_buttons(self):
        def assert_tab_ready(active_tab, buttons=()):
            self.assertTrue(
                self.browser.find_by_css(f"ul.nav-tabs a.nav-link.active[aria-controls='{active_tab}']", wait_time=10)
            )
            tab_buttons = self.browser.find_by_css(f"#{active_tab} > div:first-of-type").find_by_css("a, button")
            self.assertEqual(len(buttons), len(tab_buttons))
            for tab_button in tab_buttons:
                # Use button `innerText` instead of `text` property, because the latter only works for visible items.
                self.assertIn(tab_button["innerText"].strip(), buttons)

        # Enable the job
        job = Job.objects.get(name="Example logging job.")
        job.enabled = True
        job.save()

        # Create a fake job result
        job_result = JobResult.objects.create(
            job_model=job,
            name=job.class_path,
            user=self.user,
            celery_kwargs={"nautobot_job_console_log": True},
            task_kwargs={"interval": 4},
            status=JobResultStatusChoices.STATUS_SUCCESS,
            date_done=timezone.now(),
        )

        # Visit the job result page
        self.browser.visit(f"{self.live_server_url}{job_result.get_absolute_url()}")
        assert_tab_ready(active_tab="main", buttons=("Re-Run", "Export Logs", "Actions", "Delete Job Result"))

        # Navigate to the "Advanced" tab
        self.browser.find_by_css("ul.nav-tabs a.nav-link[aria-controls='advanced']").click()
        assert_tab_ready(active_tab="advanced")

        # Reload the page
        self.browser.reload()
        assert_tab_ready(active_tab="advanced")

        # Navigate back to the "Job Result" tab
        self.browser.find_by_css("ul.nav-tabs a.nav-link[aria-controls='main']").click()
        assert_tab_ready(active_tab="main", buttons=("Re-Run", "Export Logs", "Actions", "Delete Job Result"))

        # Navigate to the "Console Log" tab
        self.browser.find_by_css("ul.nav-tabs a.nav-link[aria-controls='job_console_entries']").click()
        assert_tab_ready(active_tab="job_console_entries", buttons=("Export Console Logs",))

        # Navigate to the "Advanced" tab again
        self.browser.find_by_css("ul.nav-tabs a.nav-link[aria-controls='advanced']").click()
        assert_tab_ready(active_tab="advanced")

        # Go back in the browser
        self.browser.back()
        assert_tab_ready(active_tab="job_console_entries", buttons=("Export Console Logs",))
