from datetime import datetime

from django.contrib.contenttypes.models import ContentType

from selenium.webdriver.common.keys import Keys

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models.jobs import Job, JobLogEntry, JobResult
from nautobot.utilities.testing.integration import SeleniumTestCase


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
            obj_type=ContentType.objects.get_for_model(Job),
            user=self.user,
            status=JobResultStatusChoices.STATUS_RUNNING,
            job_id=job.pk,
        )
        job_result.save()

        # Create fake log entries
        for i, log_level in enumerate(["default", "info", "success", "warning"]):
            JobLogEntry.objects.create(
                log_level=log_level,
                grouping="run",
                job_result=job_result,
                message=f"Log {i + 1}",
            )

        # Complete the job
        job_result.completed = datetime.now()
        job_result.status = JobResultStatusChoices.STATUS_COMPLETED
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
        self.assertEqual(4, len(visible_rows()))

        # Test for message (one row should be visible)
        filter_element.fill("")
        filter_element.type("Log 1")
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual("Default", get_cell_value(1, log_level_column))
        self.assertEqual("Log 1", get_cell_value(1, message_column))

        # Test for log level (one row should be visible)
        filter_element.fill("")
        filter_element.type("Warning")
        self.assertEqual(1, len(visible_rows()))
        # Check whether the filtered row is visible
        self.assertEqual("Warning", get_cell_value(1, log_level_column))
        self.assertEqual("Log 4", get_cell_value(1, message_column))

        # Test for log level or message with regex (two rows should be visible)
        filter_element.fill("")
        filter_element.type("(Log 2)|(Suc)")
        self.assertEqual(2, len(visible_rows()))
        # Check whether the filtered rows are visible
        self.assertEqual("Info", get_cell_value(1, log_level_column))
        self.assertEqual("Log 2", get_cell_value(1, message_column))
        self.assertEqual("Success", get_cell_value(2, log_level_column))
        self.assertEqual("Log 3", get_cell_value(2, message_column))

        # Test hitting return while the filter input is focused doesn't submit the form (producing a 405)
        active_web_element = self.browser.driver.switch_to.active_element
        active_web_element.send_keys(Keys.ENTER)
        self.assertTrue(self.browser.is_text_present("Job Result"))
