import time

from django.conf import settings

from nautobot.dcim.models import Device, Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.jobs import IntegerVar, ObjectVar, Job, JobHookReceiver, JobButtonReceiver


name = "ExamplePlugin jobs"


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

    def run(self, data, commit):
        interval = data["interval"]
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


class ExampleSimpleJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Simple Job Button Receiver"

    def receive_job_button(self, obj):
        self.log_info(obj=obj, message="Running Job Button Receiver.")
        # Add job logic here


class ExampleComplexJobButtonReceiver(JobButtonReceiver):
    class Meta:
        name = "Example Complex Job Button Receiver"

    def _run_site_job(self, obj):
        self.log_info(obj=obj, message="Running Site Job Button Receiver.")
        # Run Site Job function

    def _run_device_job(self, obj):
        self.log_info(obj=obj, message="Running Device Job Button Receiver.")
        # Run Device Job function

    def receive_job_button(self, obj):
        if isinstance(obj, Site):
            self._run_site_job(obj)
        elif isinstance(obj, Device):
            self._run_device_job(obj)
        else:
            self.log_failure(obj=obj, message=f"Unable to run Job Button for type {type(obj).__name__}.")


class ExampleSiteObjectJob(Job):
    site = ObjectVar(model=Site)

    class Meta:
        name = "Example Object Job - Site"
        description = "I'm an example job that takes a Site object as an input"

    def run(self, data, commit):
        site = data["site"]
        if commit:
            _run_site_job(self, site)


class ExampleDeviceObjectJob(Job):
    device = ObjectVar(model=Device)

    class Meta:
        name = "Example Object Job - Device"
        description = "I'm an example job that takes a Device object as an input"

    def run(self, data, commit):
        device = data["device"]
        if commit:
            _run_device_job(self, device)


class ExampleJobButtonReceiverOtherJobs(JobButtonReceiver):
    class Meta:
        name = "Example Job Button Receiver for Other Jobs"

    def receive_job_button(self, obj):
        if isinstance(obj, Site):
            _run_site_job(self, obj)
        elif isinstance(obj, Device):
            _run_device_job(self, obj)
        else:
            self.log_failure(obj=obj, message=f"Unable to run Job Button for type {type(obj).__name__}.")


def _run_site_job(job_class, obj):
    job_class.log_info(obj=obj, message="Running Site Job.")
    # Add Site job logic here


def _run_device_job(job_class, obj):
    job_class.log_info(obj=obj, message="Running Device Job.")
    # Add Device job logic here


jobs = (
    ExampleJob,
    ExampleHiddenJob,
    ExampleLoggingJob,
    ExampleJobHookReceiver,
    ExampleSimpleJobButtonReceiver,
    ExampleComplexJobButtonReceiver,
    ExampleSiteObjectJob,
    ExampleDeviceObjectJob,
    ExampleJobButtonReceiverOtherJobs,
)
