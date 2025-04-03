import copy
import hashlib

try:
    from coverage import Coverage

    has_coverage = True
except ImportError:
    has_coverage = False

from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder
from django.test.runner import _init_worker, DiscoverRunner, ParallelTestSuite
from django.test.utils import get_unique_databases_and_mirrors, NullTimeKeeper, override_settings

from nautobot.core.celery import app, setup_nautobot_job_logging
from nautobot.core.settings_funcs import parse_redis_connection


def init_worker_with_unique_cache(*args, **kwargs):
    """Extend Django's default parallel unit test setup to also ensure distinct Redis caches."""
    _init_worker(*args, **kwargs)  # call Django default to set _worker_id and set up parallel DB instances
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
    Custom test runner that excludes (slow) integration and migration tests by default.

    This test runner is aware of our use of the "integration" tag and only runs integration tests if
    explicitly passed in with `nautobot-server test --tag integration`.
    Similarly, it only runs migration tests if explicitly called with `--tag migration_test`.

    By Nautobot convention, integration tests must be tagged with "integration". The base
    `nautobot.core.testing.integration.SeleniumTestCase` has this tag, therefore any test cases
    inheriting from that class do not need to be explicitly tagged.

    Only integration tests that DO NOT inherit from `SeleniumTestCase` will need to be explicitly tagged.

    Similarly, the `django-test-migrations` package `MigratorTestCase` base class has the tag `migration_test`, so
    any subclasses thereof do not need to be explicitly tagged.
    """

    parallel_test_suite = NautobotParallelTestSuite

    exclude_tags = ["integration", "migration_test"]

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--cache-test-fixtures",
            action="store_true",
            help="Save test database to a json fixture file to re-use on subsequent tests.",
        )
        parser.add_argument(
            "--no-reusedb",
            action="store_false",
            dest="reusedb",
            help="Supplement to --keepdb; if --no-reusedb is set an existing database will NOT be reused.",
        )

    def __init__(self, cache_test_fixtures=False, reusedb=True, **kwargs):
        self.cache_test_fixtures = cache_test_fixtures
        self.reusedb = reusedb

        incoming_tags = kwargs.get("tags") or []
        exclude_tags = kwargs.get("exclude_tags") or []

        for default_excluded_tag in self.exclude_tags:
            if default_excluded_tag not in incoming_tags:
                exclude_tags.append(default_excluded_tag)
                # Can't just use self.log() here because we haven't yet called super().__init__()
                if logger := kwargs.get("logger"):
                    logger.info("Implicitly excluding tests tagged %r", default_excluded_tag)
                elif kwargs.get("verbosity", 1) >= 1:
                    print(f"Implicitly excluding tests tagged {default_excluded_tag!r}")

        kwargs["exclude_tags"] = exclude_tags

        super().__init__(**kwargs)

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

        # Nautobot specific - disable coverage measurement to improve performance of (slow) database setup
        cov = None
        if has_coverage:
            cov = Coverage.current()
        if cov is not None:
            cov.stop()

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
                            keepdb=self.keepdb
                            # Extra check added for Nautobot:
                            and self.reusedb,
                            serialize=connection.settings_dict["TEST"].get("SERIALIZE", True),
                        )

                    # Extra block added for Nautobot
                    if settings.TEST_USE_FACTORIES:
                        command = ["generate_test_data", "--flush", "--no-input"]
                        if settings.TEST_FACTORY_SEED is not None:
                            command += ["--seed", settings.TEST_FACTORY_SEED]
                        if self.cache_test_fixtures:
                            command += ["--cache-test-fixtures"]
                            # Use the list of applied migrations as a unique hash to keep fixtures from differing
                            # branches/releases of Nautobot in separate files.
                            hexdigest = hashlib.shake_128(
                                ",".join(
                                    sorted(f"{m.app}.{m.name}" for m in MigrationRecorder.Migration.objects.all())  # pylint: disable=no-member
                                ).encode("utf-8")
                            ).hexdigest(10)
                            command += ["--fixture-file", f"development/factory_dump.{hexdigest}.json"]
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
                                    # Extra checks added for Nautobot:
                                    and not settings.TEST_USE_FACTORIES
                                    and self.reusedb,
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

        # Nautobot specific - resume test coverage measurement
        if cov is not None:
            cov.start()

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
                            and not settings.TEST_USE_FACTORIES,  # with factory data, clones cannot be reused
                        )

                # Extra block added for Nautobot
                if settings.TEST_USE_FACTORIES:
                    db_name = connection.alias
                    print(f'Emptying test database "{db_name}"...')
                    call_command("flush", "--no-input", "--database", db_name)
                    print(f"Database {db_name} emptied!")

                connection.creation.destroy_test_db(old_name, self.verbosity, self.keepdb)
