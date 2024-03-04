from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Device, Location
from nautobot.extras.jobs import get_task_logger, JobButtonReceiver

logger = get_task_logger(__name__)


class TestJobButtonReceiverSimple(JobButtonReceiver):
    def receive_job_button(self, obj):
        logger.info("user: %s", self.user.username)
        logger.info(obj.name)


class TestJobButtonReceiverComplex(JobButtonReceiver):
    def receive_job_button(self, obj):
        logger.info("user: %s", self.user.username)
        if isinstance(obj, Device):
            logger.info("Device: %s", obj)
        elif isinstance(obj, Location):
            logger.info("Location: %s", obj)


class TestJobButtonReceiverFail(JobButtonReceiver):
    pass


register_jobs(TestJobButtonReceiverComplex, TestJobButtonReceiverFail, TestJobButtonReceiverSimple)
