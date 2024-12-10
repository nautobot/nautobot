import sys
import time

from django.conf import settings
from django.db import transaction

from nautobot.apps.jobs import (
    DryRunVar,
    FileVar,
    IntegerVar,
    Job,
    JobButtonReceiver,
    JobHookReceiver,
    JSONVar,
    register_jobs,
    StringVar,
)
from nautobot.dcim.models import Device, Location
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import get_task_logger

name = "Example App jobs"


class ExampleDryRunJob(Job):
    dryrun = DryRunVar()

    class Meta:
        approval_required = True
        has_sensitive_variables = False
        description = "Example job to remove serial number on all devices, supports dryrun mode."

    def run(self, dryrun):
        try:
            with transaction.atomic():
                devices_with_serial = Device.objects.exclude(serial="")
                log_msg = "Removing serial on %s devices."
                if dryrun:
                    log_msg += " (DRYRUN)"
                self.logger.info(log_msg, devices_with_serial.count())
                for device in devices_with_serial:
                    if not dryrun:
                        device.serial = ""
                        device.save()
        except Exception:
            self.logger.error("%s failed. Database changes rolled back.", self.__name__)
            raise
        self.logger.success("We can use the success log level to indicate success.")
        # Ensure get_task_logger can also use success.
        logger = get_task_logger(__name__)
        logger.success("We can also use the success log level in get_task_logger.")


class ExampleJob(Job):
    some_json_data = JSONVar(label="JSON", description="Example JSONVar for a job.", default={})

    # specify template_name to override the default job scheduling template
    template_name = "example_app/example_with_custom_template.html"

    class Meta:
        name = "Example job, does nothing"
        description = """
            Markdown Formatting

            *This is italicized*
        """

    def run(self, some_json_data):
        # some_json_data is passed to the run method as a Python object (e.g. dictionary)
        pass


class ExampleCustomFormJob(Job):
    """This job provides a simple HTML form instead of the dynamically generated form.

    The Nautobot `Job` base class provides a mechanism to automatically generate a form
    to be displayed in the run view. This covers most use cases for displaying job
    input forms. However, it is sometimes necessary to provide some customization
    in the view. This particular job will simply replace the form element with
    a different element.
    """

    # Nautobot jobs use the script variables to generate the dynamic form, but
    # this form is also used for processing the submitted data. Therefore, to
    # get data into a submitted job, script vars must be used and the submitted
    # form field names must match these script var names. As long as the
    # form field name matches this and includes an id matching `id_{form_field_name}` then
    # everything should work as expected.
    #
    # The `StringVar` here would display a simple input field, but we are going to
    # display a text area instead in the template.
    custom_job_data = StringVar(label="Input Data", description="Some input data", default="Lorem Ipsum")

    # specify template_name to override the default job scheduling template
    template_name = "example_app/custom_job_form.html"

    class Meta:
        name = "Custom form."
        has_sensitive_variables = False

    def run(self, custom_job_data):
        """Run the job."""
        self.logger.debug("Data is %s", custom_job_data)


class ExampleHiddenJob(Job):
    class Meta:
        hidden = True
        name = "Example hidden job"
        description = "I should not show in the UI!"

    def run(self):
        pass


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
        self.logger.debug("Running for %s seconds.", interval)
        for step in range(1, interval + 1):
            time.sleep(1)
            self.logger.info("Step %s", step)
            print(f"stdout logging for step {step}, task: {self.request.id}")
            print(f"stderr logging for step {step}, task: {self.request.id}", file=sys.stderr)
        self.logger.critical(
            "This log message will not be logged to the database but will be logged to the console.",
            extra={"skip_db_logging": True},
        )
        self.logger.info("Success", extra={"object": self.job_model, "grouping": "job_run_success"})
        return f"Ran for {interval} seconds"


class ExampleFileInputOutputJob(Job):
    input_file = FileVar(description="Text file to transform")

    class Meta:
        name = "Example File Input/Output job"
        description = "Takes a file as input and reverses its line order, creating a new file as output."

    def run(self, input_file):
        # Note that input_file is always opened in binary mode, so we need to decode it to a str
        text = input_file.read().decode("utf-8")
        output = "\n".join(reversed(text.split("\n")))
        # create_file(filename, content) can take either str or bytes as content
        self.create_file("output.txt", output)


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
        self.logger.info("DIFF: %s", snapshots["differences"])

        # validate changes to serial field
        if "serial" in snapshots["differences"]["added"]:
            old_serial = snapshots["differences"]["removed"]["serial"]
            new_serial = snapshots["differences"]["added"]["serial"]
            self.logger.info("%s serial has been changed from %s to %s", changed_object, old_serial, new_serial)

            # Check the new serial is valid and revert if necessary
            if not self.validate_serial(new_serial):
                changed_object.serial = old_serial
                changed_object.save()
                self.logger.info("%s serial %s was not valid. Reverted to %s", changed_object, new_serial, old_serial)

            self.logger.info("Serial validation completed for %s", changed_object)

    def validate_serial(self, serial):
        # add business logic to validate serial
        return False


class ExampleSimpleJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Simple Job Button Receiver"

    def receive_job_button(self, obj):
        self.logger.info("Running Job Button Receiver.", extra={"object": obj})
        # Add job logic here


class ExampleComplexJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Complex Job Button Receiver"

    def _run_location_job(self, obj):
        self.logger.info("Running Location Job Button Receiver.", extra={"object": obj})
        # Run Location Job function

    def _run_device_job(self, obj):
        self.logger.info("Running Device Job Button Receiver.", extra={"object": obj})
        # Run Device Job function

    def receive_job_button(self, obj):
        user = self.user
        if isinstance(obj, Location):
            if not user.has_perm("dcim.add_location"):
                self.logger.error("User '%s' does not have permission to add a Location.", user, extra={"object": obj})
            else:
                self._run_location_job(obj)
        elif isinstance(obj, Device):
            if not user.has_perm("dcim.add_device"):
                self.logger.error("User '%s' does not have permission to add a Device.", user, extra={"object": obj})
            else:
                self._run_device_job(obj)
        else:
            self.logger.error("Unable to run Job Button for type %s.", type(obj).__name__, extra={"object": obj})


class ExampleSingletonJob(Job):
    class Meta:
        name = "Example job, only one can run at any given time."
        is_singleton = True

    def run(self):
        time.sleep(60)


jobs = (
    ExampleDryRunJob,
    ExampleJob,
    ExampleCustomFormJob,
    ExampleHiddenJob,
    ExampleLoggingJob,
    ExampleFileInputOutputJob,
    ExampleJobHookReceiver,
    ExampleSimpleJobButtonReceiver,
    ExampleComplexJobButtonReceiver,
    ExampleSingletonJob,
)
register_jobs(*jobs)
