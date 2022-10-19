import yaml

from django.core.management import call_command
from django.conf import settings
from django.test.runner import DiscoverRunner


class NautobotTestRunner(DiscoverRunner):
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

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)

        if settings.TEST_USE_FACTORIES:
            print("Pre-populating test database with factory data...")
            command = ["generate_test_data", "--flush", "--no-input"]
            if settings.TEST_FACTORY_SEED is not None:
                command += ["--seed", settings.TEST_FACTORY_SEED]
            call_command(*command)

        return result

    def teardown_databases(self, old_config, **kwargs):
        if settings.TEST_USE_FACTORIES:
            print("Emptying test database...")
            call_command("flush", "--no-input")
            print("Database emptied!")

        super().teardown_databases(old_config, **kwargs)


# Use django_slowtests only when GENERATE_PERFORMANCE_REPORT flag is set to true
try:
    from django_slowtests.testrunner import DiscoverSlowestTestsRunner

    print("Using NautobotPerformanceTestRunner to run tests ...")

    class NautobotPerformanceTestRunner(NautobotTestRunner, DiscoverSlowestTestsRunner):
        """
        Pre-requisite:
            Set `GENERATE_PERFORMANCE_REPORT` to True in settings.py
        This test runner is designated to run performance specific unit tests.

        `ModelViewTestCase` is tagged with `performance` to test the time it will take to retrieve, list, create, bulk_create,
        delete, bulk_delete, edit, bulk_edit object(s) and various other operations.

        The results are compared to the corresponding entries in `TEST_PERFORMANCE_BASELINE_FILE` and only results that are significantly slower
        than baseline will be exposed to the user.
        """

        def generate_report(self, test_results, result):
            """
            Generate Performance Report consists of unit tests that are significantly slower than baseline.
            """
            test_result_count = len(test_results)

            # Add `--performance-snapshot` to the end of `invoke` commands to generate a report.json file consist of the performance tests result
            if self.report_path:
                data = [
                    {
                        "tests": [
                            {
                                "name": func_name,
                                "execution_time": float(timing),
                            }
                            for func_name, timing in test_results
                        ],
                        "test_count": result.testsRun,
                        "failed_count": len(result.errors + result.failures),
                        "total_execution_time": result.timeTaken,
                    }
                ]
                with open(self.report_path, "w") as outfile:
                    yaml.dump(data, outfile, sort_keys=False)
            # Print the results in the CLI.
            else:
                if test_result_count:
                    print(f"\n{test_result_count} abnormally slower tests:")
                    for func_name, timing in test_results:
                        time = float(timing)
                        baseline = self.baselines.get(func_name, None)
                        if baseline:
                            baseline = float(baseline)
                            print(f"{time:.4f}s {func_name} is significantly slower than the baseline {baseline:.4f}s")
                        else:
                            print(
                                f"Performance baseline for {func_name} is not available. Test took {time:.4f}s to run"
                            )

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

            # add `--performance_report` to `invoke` commands to generate report.
            # e.g. `invoke unittest --performance_report`
            if not self.should_generate_report:
                self.remove_timing_tmp_files()
                return return_value

            # Grab slowest tests
            timings = self.get_timings()
            # Sort the results by test names x[0]
            by_name = sorted(timings, key=lambda x: x[0])
            test_results = by_name

            if self.baselines:
                # Filter tests by baseline numbers
                test_results = []

                for entry in by_name:
                    # Convert test time from seconds to miliseconds for comparison
                    result_time_ms = entry[1] * 1000
                    # If self.report_path, that means the user wants to update the performance baselines.
                    # so we append every result that is available to us.
                    if self.report_path:
                        test_results.append(entry)
                    else:
                        # If the test is completed under 1.5 times the baseline or the difference between the result and the baseline is less than 3 seconds,
                        # dont show the test to the user.

                        baseline = self.baselines.get(entry[0], None)

                        # check if baseline is available
                        if not baseline:
                            test_results.append(entry)
                            continue

                        # baseline duration in milliseconds
                        baseline_ms = baseline * 1000
                        # Arbitrary criteria to not make performance test fail easily
                        if result_time_ms <= baseline_ms * 1.5 or result_time_ms - baseline_ms <= 500:
                            continue

                        test_results.append(entry)

            self.generate_report(test_results, result)
            return return_value

except ImportError:
    print(
        "Unable to import DiscoverSlowestTestsRunner from `django_slowtests`. Is the 'django_slowtests' package installed?"
    )
