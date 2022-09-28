from django.core.management import call_command
from django.test.runner import DiscoverRunner

import factory.random

from nautobot.ipam.factory import AggregateFactory, RIRFactory
from nautobot.tenancy.factory import TenantFactory, TenantGroupFactory


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
