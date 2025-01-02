from nautobot.apps.jobs import Job


class ChildJob(Job):
    def run(self):  # pylint:disable=arguments-differ
        pass
