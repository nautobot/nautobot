from nautobot.extras.jobs import JobHookReceiver
from nautobot.dcim.models import Site


class TestJobHookReceiverLog(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        self.log_info(f"change: {change}")
        self.log_info(f"action: {action}")
        self.log_info(f"request.user: {self.request.user.username}")
        self.log_success(changed_object.name)


class TestJobHookReceiverChange(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        Site.objects.create(name="test_jhr")


class TestJobHookReceiverFail(JobHookReceiver):
    pass
