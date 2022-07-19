from nautobot.extras.jobs import JobHookReceiver, StringVar
from nautobot.dcim.models import Site


class TestJobHookReceiverLog(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        self.log_info(f"change: {change}")
        self.log_info(f"action: {action}")
        self.log_success(changed_object.name)


class TestJobHookReceiverChange(JobHookReceiver):
    a_testvar_b_first = StringVar()
    a_testvar_a_second = StringVar()

    def receive_job_hook(self, change, action, changed_object):
        Site.objects.create(name="test_jhr")


class TestJobHookReceiverFail(JobHookReceiver):
    pass
