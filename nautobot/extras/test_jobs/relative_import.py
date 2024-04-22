from fail import TestFail

from nautobot.apps.jobs import register_jobs


class TestReallyPass(TestFail):
    def run(self):
        pass


register_jobs(TestReallyPass)
