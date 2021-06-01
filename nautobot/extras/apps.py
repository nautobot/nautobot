import logging

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
