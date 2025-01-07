from fail import TestFailJob  # pylint: disable=import-error

from nautobot.apps.jobs import register_jobs


class TestReallyPass(TestFailJob):
    def run(self):  # pylint: disable=arguments-differ
        pass


register_jobs(TestReallyPass)
