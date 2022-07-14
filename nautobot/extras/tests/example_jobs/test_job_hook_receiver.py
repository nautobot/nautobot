from nautobot.extras.jobs import JobHookReceiver
from nautobot.dcim.models import Site


class TestJobHookReceiverLog(JobHookReceiver):
    def run(self, data, commit):
        object_change = data["object_change"]
        self.log_success(object_change.changed_object.name)


class TestJobHookReceiverChange(JobHookReceiver):
    def run(self, data, commit):
        Site.objects.create(name="test_jhr")
