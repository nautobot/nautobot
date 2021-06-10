from django.core.management import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connections


class NautobotBase(BaseCommand):
    migration_notice = "Run 'nautobot-server migrate' to apply them."

    def check_migrations(self) -> None:
        """
        Print a warning if the set of migrations on disk don't match the
        migrations in the database.
        """
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        except ImproperlyConfigured:
            # No databases are configured (or the dummy one)
            return

        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            apps_waiting_migration = sorted({migration.app_label for migration, backwards in plan})
            self.stdout.write(
                self.style.NOTICE(
                    "\nYou have %(unapplied_migration_count)s unapplied migration(s). "
                    "Your project may not work properly until you apply the "
                    "migrations for app(s): %(apps_waiting_migration)s."
                    % {
                        "unapplied_migration_count": len(plan),
                        "apps_waiting_migration": ", ".join(apps_waiting_migration),
                    }
                )
            )
            self.stdout.write(self.style.NOTICE(self.migration_notice))
