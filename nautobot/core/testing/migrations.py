from unittest import skip

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase


@skip("TODO: Havoc has been wreaked on migrations in 2.0, so this test is currently broken.")
class NautobotDataMigrationTest(TestCase):
    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name

    migrate_from = None
    migrate_to = None

    def setUp(self):
        # Remove factory data beforehand
        call_command("flush", "--no-input")

        error_message = f"DataMigrationTest '{type(self).__name__}' must define migrate_from and migrate_to properties"
        self.assertNotEqual(self.migrate_from, None, error_message)
        self.assertNotEqual(self.migrate_to, None, error_message)

        # migrate nautobot to the previous migration state
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        executor.migrate(self.migrate_from)

        self.populateDataBeforeMigration(old_apps)

        # migrate nautobot to the migration you want to test against
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload

        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def populateDataBeforeMigration(self, installed_apps):
        """Populate your Nautobot data before migrating from the first migration to the second"""
