import copy

from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.test.runner import _init_worker, DiscoverRunner, ParallelTestSuite
from django.test.utils import get_unique_databases_and_mirrors, NullTimeKeeper, override_settings
import yaml

from nautobot.core.celery import app, setup_nautobot_job_logging
from nautobot.core.settings_funcs import parse_redis_connection


def init_worker_with_unique_cache(counter):
    """Extend Django's default parallel unit test setup to also ensure distinct Redis caches."""
    _init_worker(counter)  # call Django default to set _worker_id and set up parallel DB instances
    # _worker_id is now 1, 2, 3, 4, etc.

    from django.test.runner import _worker_id

    # Redis DB indices 0 and 1 are used by non-automated testing, so we want to start at index 2
    caches = copy.deepcopy(settings.CACHES)
    caches["default"]["LOCATION"] = parse_redis_connection(redis_database=_worker_id + 1)
    override_settings(CACHES=caches).enable()
    print(f"Set settings.CACHES['default']['LOCATION'] to use Redis index {_worker_id + 1}")


class NautobotParallelTestSuite(ParallelTestSuite):
    init_worker = init_worker_with_unique_cache


class NautobotTestRunner(DiscoverRunner):
    """
    Custom test runner that excludes integration tests by default.

    This test runner is aware of our use of the "integration" tag and only runs integration tests if
    explicitly passed in with `nautobot-server test --tag integration`.

    By Nautobot convention, integration tests must be tagged with "integration". The base
    `nautobot.core.testing.integration.SeleniumTestCase` has this tag, therefore any test cases
    inheriting from that class do not need to be explicitly tagged.

    Only integration tests that DO NOT inherit from `SeleniumTestCase` will need to be explicitly tagged.
    """

    parallel_test_suite = NautobotParallelTestSuite

    exclude_tags = ["integration"]

    def __init__(self, cache_test_fixtures=False, **kwargs):
        self.cache_test_fixtures = cache_test_fixtures

        # Assert "integration" hasn't been provided w/ --tag
        incoming_tags = kwargs.get("tags") or []
        # Assert "exclude_tags" hasn't been provided w/ --exclude-tag; else default to our own.
        incoming_exclude_tags = kwargs.get("exclude_tags") or []

        # Only include our excluded tags if "integration" isn't provided w/ --tag
        if "integration" not in incoming_tags:
            incoming_exclude_tags.extend(self.exclude_tags)
            kwargs["exclude_tags"] = incoming_exclude_tags

        super().__init__(**kwargs)

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--cache-test-fixtures",
            action="store_true",
            help="Save test database to a json fixture file to re-use on subsequent tests.",
        )

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # Remove 'testserver' that Django "helpfully" adds automatically to ALLOWED_HOSTS, masking issues like #3065
        settings.ALLOWED_HOSTS.remove("testserver")
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            # Make sure logs get captured when running Celery tasks, even though we don't have/need a Celery worker
            setup_nautobot_job_logging(None, None, app.conf)

    def setup_databases(self, **kwargs):
        # Adapted from Django 3.2 django.test.utils.setup_databases
        time_keeper = self.time_keeper
        if time_keeper is None:
            time_keeper = NullTimeKeeper()

        test_databases, mirrored_aliases = get_unique_databases_and_mirrors(kwargs.get("aliases", None))

        old_names = []

        for db_name, aliases in test_databases.values():
            first_alias = None
            for alias in aliases:
                connection = connections[alias]
                old_names.append((connection, db_name, first_alias is None))

                # Actually create the database for the first connection
                if first_alias is None:
                    first_alias = alias
                    with time_keeper.timed(f"  Creating '{alias}'"):
                        connection.creation.create_test_db(
                            verbosity=self.verbosity,
                            autoclobber=not self.interactive,
                            keepdb=self.keepdb,
                            serialize=connection.settings_dict["TEST"].get("SERIALIZE", True),
                        )

                    # Extra block added for Nautobot
                    if settings.TEST_USE_FACTORIES:
                        command = ["generate_test_data", "--flush", "--no-input"]
                        if settings.TEST_FACTORY_SEED is not None:
                            command += ["--seed", settings.TEST_FACTORY_SEED]
                        if self.cache_test_fixtures:
                            command += ["--cache-test-fixtures"]
                        with time_keeper.timed(f'  Pre-populating test database "{alias}" with factory data...'):
                            db_command = [*command, "--database", alias]
                            call_command(*db_command)

                    if self.parallel > 1:
                        for index in range(self.parallel):
                            with time_keeper.timed(f"  Cloning '{alias}'"):
                                connection.creation.clone_test_db(
                                    suffix=str(index + 1),
                                    verbosity=self.verbosity,
                                    keepdb=self.keepdb
                                    # Extra check added for Nautobot:
                                    and not settings.TEST_USE_FACTORIES,
                                )

                # Configure all other connections as mirrors of the first one
                else:
                    connection.creation.set_as_test_mirror(connections[first_alias].settings_dict)

        # Configure the test mirrors
        for alias, mirror_alias in mirrored_aliases.items():
            connections[alias].creation.set_as_test_mirror(connections[mirror_alias].settings_dict)

        if self.debug_sql:
            for alias in connections:
                connections[alias].force_debug_cursor = True

        return old_names

    def teardown_databases(self, old_config, **kwargs):
        # Adapted from Django 3.2 django.test.utils.teardown_databases
        for connection, old_name, destroy in old_config:
            if destroy:
                if self.parallel > 1:
                    for index in range(self.parallel):
                        connection.creation.destroy_test_db(
                            suffix=str(index + 1),
                            verbosity=self.verbosity,
                            keepdb=self.keepdb
                            # Extra check added for Nautobot
                            and not settings.TEST_USE_FACTORIES,
                        )

                # Extra block added for Nautobot
                if settings.TEST_USE_FACTORIES:
                    db_name = connection.alias
                    print(f'Emptying test database "{db_name}"...')
                    call_command("flush", "--no-input", "--database", db_name)
                    print(f"Database {db_name} emptied!")

                connection.creation.destroy_test_db(old_name, self.verbosity, self.keepdb)


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
