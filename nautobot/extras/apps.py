import logging

from health_check.plugins import plugin_dir
from nautobot.core.apps import NautobotConfig
from django.db.utils import ProgrammingError


logger = logging.getLogger("nautobot.extras.apps")


class ExtrasConfig(NautobotConfig):
    name = "nautobot.extras"

    def ready(self):
        super().ready()
        import nautobot.extras.signals  # noqa
        from nautobot.extras.plugins.validators import wrap_model_clean_methods

        try:
            # Wrap plugin model validator registered clean methods
            wrap_model_clean_methods()
        except ProgrammingError:
            # The ContentType table might not exist yet (if migrations have not been run)
            logger.warning(
                "Wrapping model clean methods for custom validators failed because "
                "the ContentType table was not available or populated. This is normal "
                "during the execution of the migration command for the first time."
            )

        # Register the DatabaseBackend health check
        from nautobot.extras.health_checks import DatabaseBackend, RedisBackend

        plugin_dir.register(DatabaseBackend)
        plugin_dir.register(RedisBackend)
