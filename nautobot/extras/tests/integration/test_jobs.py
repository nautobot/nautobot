from django.utils import timezone
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models.jobs import Job, JobLogEntry, JobResult


class JobResultTest(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

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
        self.browser.find_by_xpath("//table[@class='table table-hover table-headings']/tbody/tr[1]/td[2]/a").click()

        filter_element = self.browser.find_by_xpath("//input[@class='form-control log-filter']")
        visible_rows_xpath = "//table[@id='logs']/tbody/tr[not(contains(@style, 'display: none'))]"

        def visible_rows():
            return self.browser.find_by_xpath(visible_rows_xpath)

        def get_cell_value(row, column):
            return self.browser.find_by_xpath(f"{visible_rows_xpath}[{row}]/td[{column}]").text

        log_level_column = 3
        message_column = 5

        # Sanity check
        self.assertEqual(len(LogLevelChoices.values()), len(visible_rows()))

        # Test for message (one row should be visible)
        filter_element.fill("")
        filter_element.type(log_entries[0].message)
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual(log_entries[0].log_level.title(), get_cell_value(1, log_level_column))
        self.assertEqual(log_entries[0].message, get_cell_value(1, message_column))

        # Test for log level (one row should be visible)
        filter_element.fill("")
        filter_element.type(log_entries[3].log_level.title())
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual(log_entries[3].log_level.title(), get_cell_value(1, log_level_column))
        self.assertEqual(log_entries[3].message, get_cell_value(1, message_column))

        # Test for log level or message with regex (two rows should be visible)
        filter_element.fill("")
        filter_element.type(f"({log_entries[1].message})|({log_entries[2].log_level[:3].title()})")
        self.assertEqual(2, len(visible_rows()))
        # Check whether the filtered rows are visible
        self.assertEqual(log_entries[1].log_level.title(), get_cell_value(1, log_level_column))
        self.assertEqual(log_entries[1].message, get_cell_value(1, message_column))
        self.assertEqual(log_entries[2].log_level.title(), get_cell_value(2, log_level_column))
        self.assertEqual(log_entries[2].message, get_cell_value(2, message_column))

        # Test hitting return while the filter input is focused doesn't submit the form (producing a 405)
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        self.assertTrue(self.browser.is_text_present("Job Result"))
