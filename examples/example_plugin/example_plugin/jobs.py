import pprint
import time

from celery.utils.log import get_task_logger
from django.conf import settings

from nautobot.core.celery import app
from nautobot.dcim.models import Manufacturer
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import BooleanVar, IntegerVar, Job, JobHookReceiver, ObjectVar


logger = get_task_logger(__name__)
name = "ExamplePlugin jobs"


class TestObjectJob(Job):
    obj = ObjectVar(model=Manufacturer, description="Select any object")

    def run(self, obj):
        # obj = Manufacturer.objects.get(pk=obj)
        self.log_info(f"OBJECT PASSED IN: {obj}")
        self.log_info(f"TYPE OF OBJECT PASSED IN: {obj.__class__.__name__}")


class ListTasks(Job):
    def run(self):
        logger.info(f"LIST OF TASKS: {pprint.pformat(app.tasks)}")


class MultiplyJob(Job):
    """PROTOTYPE:
    from nautobot.core.celery import app
    t=app.tasks["MultiplyJob"]
    from nautobot.extras.utils import get_job_content_type
    j=Job.objects.get(name="MultiplyJob")
    jr=JobResult.enqueue_job(j, User.objects.first(), celery_kwargs={}, x=4, y=5, dryrun=False)
    """

    # name = "example_plugin.jobs.MultiplyJob"
    x = IntegerVar()
    y = IntegerVar()
    dryrun = BooleanVar()

    class Meta:
        approval_required = True
        has_sensitive_variables = False

    def run(self, x, y, dryrun):
        result = x * y
        logger.info(f"TASK HEADERS: {self.request.headers}")
        logger.info(f"TASK DRYRUN: {dryrun}")
        logger.info(f"{x} * {y} = {result}")
        return result


class ExampleJob(Job):

    # specify template_name to override the default job scheduling template
    template_name = "example_plugin/example_with_custom_template.html"

    class Meta:
        name = "Example job, does nothing"
        description = """
            Markdown Formatting

            *This is italicized*
        """


class ExampleHiddenJob(Job):
    class Meta:
        hidden = True
        name = "Example hidden job"
        description = "I should not show in the UI!"


class ExampleLoggingJob(Job):
    interval = IntegerVar(default=4, description="The time in seconds to sleep.")

    class Meta:
        name = "Example logging job."
        description = "I log stuff to demonstrate how UI logging works."
        task_queues = [
            settings.CELERY_TASK_DEFAULT_QUEUE,
            "priority",
            "bulk",
        ]

    def run(self, interval):
        self.log_debug(message=f"Running for {interval} seconds.")
        for step in range(1, interval + 1):
            time.sleep(1)
            self.log_info(message=f"Step {step}")
        self.log_success(obj=None)
        return f"Ran for {interval} seconds"


class ExampleJobHookReceiver(JobHookReceiver):
    class Meta:
        name = "Example job hook receiver"
        description = "Validate changes to object serial field"

    def receive_job_hook(self, change, action, changed_object):
        # return on delete action
        if action == ObjectChangeActionChoices.ACTION_DELETE:
            return

        # log diff output
        snapshots = change.get_snapshots()
        self.log_info(f"DIFF: {snapshots['differences']}")

        # validate changes to serial field
        if "serial" in snapshots["differences"]["added"]:
            old_serial = snapshots["differences"]["removed"]["serial"]
            new_serial = snapshots["differences"]["added"]["serial"]
            self.log_info(f"{changed_object} serial has been changed from {old_serial} to {new_serial}")

            # Check the new serial is valid and revert if necessary
            if not self.validate_serial(new_serial):
                changed_object.serial = old_serial
                changed_object.save()
                self.log_info(f"{changed_object} serial {new_serial} was not valid. Reverted to {old_serial}")

            self.log_success(message=f"Serial validation completed for {changed_object}")

    def validate_serial(self, serial):
        # add business logic to validate serial
        return False


jobs = (ExampleJob, ExampleHiddenJob, ExampleLoggingJob, ExampleJobHookReceiver, ListTasks, MultiplyJob, TestObjectJob)
app.register_task(ListTasks)
app.register_task(MultiplyJob)
app.register_task(ExampleLoggingJob)
app.register_task(TestObjectJob)
