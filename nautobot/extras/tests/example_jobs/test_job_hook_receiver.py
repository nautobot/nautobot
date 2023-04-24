from nautobot.extras.jobs import JobHookReceiver
from nautobot.dcim.models import Location, LocationType


class TestJobHookReceiverLog(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        self.log_info(f"change: {change}")
        self.log_info(f"action: {action}")
        self.log_info(f"request.user: {self.request.user.username}")
        self.log_success(changed_object.name)


class TestJobHookReceiverChange(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        location_type = LocationType.objects.create(name="Job Location Type")
        Location.objects.create(name="test_jhr", location_type=location_type)


class TestJobHookReceiverFail(JobHookReceiver):
    pass
