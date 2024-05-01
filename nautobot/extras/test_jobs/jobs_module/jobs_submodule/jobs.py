from nautobot.apps.jobs import Job


class ChildJob(Job):
    def run(self):
        pass
