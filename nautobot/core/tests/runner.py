from django.conf import settings
from django.core.management import call_command
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
