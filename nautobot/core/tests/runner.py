import json
import yaml

from django.core.management import call_command
from django.conf import settings
from django_slowtests.testrunner import DiscoverSlowestTestsRunner

import factory.random

from nautobot.ipam.factory import AggregateFactory, RIRFactory
from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory


class NautobotTestRunner(DiscoverSlowestTestsRunner):
    """
    Custom test runner that excludes integration tests by default.

    This test runner is aware of our use of the "integration" tag and only runs integration tests if
    explicitly passed in with `nautobot-server test --tag integration`.

    By Nautobot convention, integration tests must be tagged with "integration". The base
    `nautobot.utilities.testing.integration.SeleniumTestCase` has this tag, therefore any test cases
    inheriting from that class do not need to be explicitly tagged.

    Only integration tests that DO NOT inherit from `SeleniumTestCase` will need to be explicitly tagged.

    `ModelViewTestCase` is tagged with `performance` to test the time it will take to retrieve, list, create, bulk_create,
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

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        print("Beginning database pre-population...")

        print("Flushing any leftover test data from previous runs...")
        call_command("flush", "--no-input")

        # Set constant seed for reproducible "randomness"
        # TODO: it would be nice to use a random seed each time (for test robustness)
        #       but also provide an option to use a specified seed to reproduce problems.
        factory.random.reseed_random("Nautobot")

        print("Creating TenantGroups...")
        TenantGroupFactory.create_batch(10, has_parent=False)
        TenantGroupFactory.create_batch(10, has_parent=True)
        print("Creating Tenants...")
        TenantFactory.create_batch(10, has_group=False)
        TenantFactory.create_batch(10, has_group=True)
        print("Creating RIRs...")
        RIRFactory.create_batch(9)  # only 9 unique RIR names are hard-coded presently
        print("Creating Aggregates...")
        AggregateFactory.create_batch(20)

        print("Database pre-population completed!")
        return result

    def teardown_databases(self, old_config, **kwargs):
        print("Emptying test database...")
        call_command("flush", "--no-input")
        print("Database emptied!")

        super().teardown_databases(old_config, **kwargs)

    def generate_report(self, test_results, result):
        """
        Generate Performance Report consists of unittests that are significantly slower than baseline.
        """
        test_result_count = len(test_results)

        # Add `--generate_report` to the end of `invoke` commands to generate a report.json file consist of the performance tests result
        if self.report_path:
            data = {
                "tests": [{"name": func_name, "execution_time": float(timing)} for func_name, timing in test_results],
                "test_count": result.testsRun,
                "failed_count": len(result.errors + result.failures),
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
                # Make the test fail if there are tests significantly slower
                assert test_result_count == 0, "Performance Tests failed due to significantly slower tests"

            if not test_results:
                print("\nNo tests signficantly slower than baseline. Success!")

    def get_baselines(self):
        """Load the performance_baselines.yml file for result comparison."""
        baselines = {}
        input_file = getattr(
            settings, "TEST_PERFORMANCE_BASELINE_FILE", "nautobot/core/tests/performance_baselines.yml"
        )

        with open(input_file) as f:
            data = yaml.safe_load(f)
            for entry in data["tests"]:
                baselines[entry["name"]] = entry["execution_time"]
        return baselines

    def suite_result(self, suite, result):
        """Compile the performance test results"""
        return_value = super(DiscoverSlowestTestsRunner, self).suite_result(suite, result)
        self.baselines = self.get_baselines()

        # You can set `TEST_ALWAYS_GENERATE_SLOW_REPORT` to True or add `--report` to `invoke` commands to generate report.
        # e.g. `invoke unittest --report`
        should_generate_report = getattr(settings, "TEST_ALWAYS_GENERATE_SLOW_REPORT") or self.should_generate_report
        if not should_generate_report:
            self.remove_timing_tmp_files()
            return return_value

        # Grab slowest tests
        timings = self.get_timings()
        # Sort the results by test names x[0]
        by_time = sorted(timings, key=lambda x: x[0])
        test_results = by_time

        if self.baselines:
            # Filter tests by baseline numbers
            test_results = []

            for entry in by_time:
                # Convert test time from seconds to miliseconds for comparison
                result_time_ms = entry[1] * 1000
                # If self.report_path, that means the user wants to update the performance baselines.
                # so we append every result that is available to us.
                if self.report_path:
                    test_results.append(entry)
                else:
                    # If the test completed under 1.5 times the baseline or the difference between the result and the baseline is less than 5 seconds,
                    # dont show the test to the user.

                    # baseline duration in milliseconds
                    baseline_ms = self.baselines.get(entry[0], 0) * 1000
                    # Arbitrary criteria to not make performance test fail easily
                    if result_time_ms <= baseline_ms * 1.5 or result_time_ms - baseline_ms <= 3000:
                        continue

                    test_results.append(entry)

        self.generate_report(test_results, result)
        return return_value
