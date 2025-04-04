from nautobot.extras.jobs import Job, JobButtonReceiver, JobHookReceiver


class MyJob(Job):
    def run(self):
        pass


class MyJobHookReceiver(JobHookReceiver):
    def receive_job_hook(self, change, action, changed_object):
        pass


class MyJobButtonReceiver(JobButtonReceiver):
    def receive_job_button(self, obj):
        pass
