import json
from django.conf import settings
from django_slowtests.testrunner import DiscoverSlowestTestsRunner

from nautobot.core.tests.__init__ import PERFORMANCE_BASELINES


class NautobotTestRunner(DiscoverSlowestTestsRunner):
    """
    Custom test runner that excludes integration tests by default.

    This test runner is aware of our use of the "integration" tag and only runs integration tests if
    explicitly passed in with `nautobot-server test --tag integration`.

    By Nautobot convention, integration tests must be tagged with "integration". The base
    `nautobot.utilities.testing.integration.SeleniumTestCase` has this tag, therefore any test cases
    inheriting from that class do not need to be explicitly tagged.

    Only integration tests that DO NOT inherit from `SeleniumTestCase` will need to be explicitly tagged.
    """

    exclude_tags = ["integration"]

    def __init__(self, **kwargs):
        # Assert "integration" hasn't been provided w/ --tag
        incoming_tags = kwargs.get("tags") or []

        # Assert "exclude_tags" hasn't been provided w/ --exclude-tag; else default to our own.
        incoming_exclude_tags = kwargs.get("exclude_tags") or []

        # Only include our excluded tags if "integration" isn't provided w/ --tag
        if "integration" not in incoming_tags:
            incoming_exclude_tags.extend(self.exclude_tags)
            kwargs["exclude_tags"] = incoming_exclude_tags

        super().__init__(**kwargs)

    def generate_report(self, test_results, result):
        test_result_count = len(test_results)

        if self.report_path:
            data = {
                "slower_tests": [
                    {"name": func_name, "execution_time": float(timing)} for func_name, timing in test_results
                ],
                "nb_tests": result.testsRun,
                "nb_failed": len(result.errors + result.failures),
                "total_execution_time": result.timeTaken,
            }
            with open(self.report_path, "w") as outfile:
                json.dump(data, outfile)
        else:
            if test_result_count:
                print(f"\n{test_result_count} abnormally slower tests:")

            for func_name, timing in test_results:
                time = float(timing)
                baseline = float(self.baselines[func_name])
                print(f"{time:.4f}s {func_name} is significantly slower than the baseline {baseline:.4f}s")

            if not test_results:
                print("\nNo tests signficantly slower than baseline")

    def get_baselines(self):
        """Get the performance baselines for comparison"""
        baselines = {}
        data = PERFORMANCE_BASELINES["slower_tests"]
        for entry in data:
            baselines[entry["name"]] = entry["execution_time"]
        return baselines

    def suite_result(self, suite, result):
        return_value = super(DiscoverSlowestTestsRunner, self).suite_result(suite, result)
        NUM_SLOW_TESTS = getattr(settings, "NUM_SLOW_TESTS", 10)
        self.baselines = self.get_baselines()

        should_generate_report = getattr(settings, "ALWAYS_GENERATE_SLOW_REPORT", True) or self.should_generate_report
        if not should_generate_report:
            self.remove_timing_tmp_files()
            return return_value

        # Grab slowest tests
        timings = self.get_timings()
        by_time = sorted(timings, key=lambda x: x[1], reverse=True)
        if by_time is not None:
            by_time = by_time[:NUM_SLOW_TESTS]
        test_results = by_time

        if self.baselines:
            # Filter tests by threshold
            test_results = []

            for entry in by_time:
                # Convert test time from seconds to miliseconds for comparison
                result_time_ms = entry[1] * 1000

                # If the test completed under 1.5 times the baseline
                # don't show it to the user
                if result_time_ms <= self.baselines[entry[0]] * 1000 * 1.8:
                    continue

                test_results.append(result)

        self.generate_report(test_results, result)
        return return_value
