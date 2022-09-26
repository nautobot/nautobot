import json
from django.conf import settings
from django_slowtests.testrunner import DiscoverSlowestTestsRunner
import yaml
from yaml.loader import SafeLoader


class NautobotTestRunner(DiscoverSlowestTestsRunner):
    """
    Custom test runner that excludes integration tests by default.

    This test runner is aware of our use of the "integration" tag and only runs integration tests if
    explicitly passed in with `nautobot-server test --tag integration`.

    By Nautobot convention, integration tests must be tagged with "integration". The base
    `nautobot.utilities.testing.integration.SeleniumTestCase` has this tag, therefore any test cases
    inheriting from that class do not need to be explicitly tagged.

    Only integration tests that DO NOT inherit from `SeleniumTestCase` will need to be explicitly tagged.

    `ModelViewSetTestCase` is tagged with `performance` to test the time it will take to retrieve, list, create, bulk_create,
    delete, bulk_delete, edit, bulk_edit object(s) and various other operations.

    The results are compared to the corresponding entries in PERFORMANCE_BASELINES and only results that are significantly slower
    than baseline will be exposed to the user.
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
        """
        Generate Performance Report consists of unittests that are significantly slower than baseline.
        """
        test_result_count = len(test_results)

        # Generate a report.json file consist of the performance tests result
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
        # Print the results in the CLI.
        else:
            if test_result_count:
                print(f"\n{test_result_count} abnormally slower tests:")
                for func_name, timing in test_results:
                    time = float(timing)
                    baseline = float(self.baselines[func_name])
                    print(f"{time:.4f}s {func_name} is significantly slower than the baseline {baseline:.4f}s")
                assert test_result_count == 0, "Performance Tests failed due to significantly slower tests"

            if not test_results:
                print("\nNo tests signficantly slower than baseline")

    def get_baselines(self):
        """Get the performance baselines for comparison"""
        baselines = {}
        input_file = "nautobot/core/tests/performance_baselines.yml"

        with open(input_file) as f:
            data = yaml.load(f, Loader=SafeLoader)
            for entry in data["tests"]:
                baselines[entry["name"]] = entry["execution_time"]
        return baselines

    def suite_result(self, suite, result):
        return_value = super(DiscoverSlowestTestsRunner, self).suite_result(suite, result)
        self.baselines = self.get_baselines()

        should_generate_report = getattr(settings, "ALWAYS_GENERATE_SLOW_REPORT", True) or self.should_generate_report
        if not should_generate_report:
            self.remove_timing_tmp_files()
            return return_value

        # Grab slowest tests
        timings = self.get_timings()
        by_time = sorted(timings, key=lambda x: x[1], reverse=True)
        test_results = by_time

        if self.baselines:
            # Filter tests by threshold
            test_results = []

            for entry in by_time:
                # Convert test time from seconds to miliseconds for comparison
                result_time_ms = entry[1] * 1000
                # If self.report_path, that means the user wants to update the performance baselines.
                # so we append every result that is available to us.
                if self.report_path:
                    test_results.append(entry)
                else:
                    # If the test completed under 1.8 times the baseline result
                    # don't show it to the user
                    if result_time_ms <= self.baselines.get(entry[0], 0) * 1000 * 1.8:
                        continue

                    test_results.append(entry)

        self.generate_report(test_results, result)
        return return_value
