from fail import TestFailJob  # type: ignore[import-not-found]  # pylint: disable=import-error

from nautobot.apps.jobs import register_jobs


class TestReallyPass(TestFailJob):
    def run(self):  # pylint: disable=arguments-differ
        pass


register_jobs(TestReallyPass)
