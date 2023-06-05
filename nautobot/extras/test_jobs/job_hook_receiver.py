from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import JobHookReceiver, get_task_logger
from nautobot.dcim.models import Location, LocationType


logger = get_task_logger(__name__)


class TestJobHookReceiverLog(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        logger.info("change: %s", change)
        logger.info("action: %s", action)
        logger.info("jobresult.user: %s", self.job_result.user.username)
        logger.info(changed_object.name)


class TestJobHookReceiverChange(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        location_type = LocationType.objects.create(name="Job Location Type")
        Location.objects.create(name="test_jhr", location_type=location_type)


class TestJobHookReceiverFail(JobHookReceiver):
    pass


register_jobs(TestJobHookReceiverChange, TestJobHookReceiverFail, TestJobHookReceiverLog)
