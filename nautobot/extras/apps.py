import logging

from django.conf import settings
from django.db.utils import ProgrammingError

import graphene
from health_check.plugins import plugin_dir

from nautobot.core.apps import NautobotConfig
from nautobot.core.signals import nautobot_database_ready


logger = logging.getLogger("nautobot.extras.apps")


class ExtrasConfig(NautobotConfig):
    name = "nautobot.extras"

    def ready(self):
        super().ready()
        import nautobot.extras.signals  # noqa
        from nautobot.extras.signals import refresh_job_models

        nautobot_database_ready.connect(refresh_job_models, sender=self)

        from graphene_django.converter import convert_django_field
        from taggit.managers import TaggableManager
        from nautobot.extras.graphql.types import TagType

        @convert_django_field.register(TaggableManager)
        def convert_field_to_list_tags(field, registry=None):
            """Convert TaggableManager to List of Tags."""
            return graphene.List(TagType)

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
        from nautobot.extras.health_checks import CacheopsRedisBackend, DatabaseBackend, RedisBackend

        plugin_dir.register(DatabaseBackend)
        plugin_dir.register(RedisBackend)
        if getattr(settings, "CACHEOPS_HEALTH_CHECK_ENABLED", False):
            plugin_dir.register(CacheopsRedisBackend)

        # Register built-in SecretsProvider classes
        from nautobot.extras.secrets.providers import EnvironmentVariableSecretsProvider, TextFileSecretsProvider
        from nautobot.extras.secrets import register_secrets_provider

        register_secrets_provider(EnvironmentVariableSecretsProvider)
        register_secrets_provider(TextFileSecretsProvider)
