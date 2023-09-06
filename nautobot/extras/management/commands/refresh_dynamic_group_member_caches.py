from django.apps import apps
from django.core.cache import cache
from django.core.management.base import BaseCommand

from nautobot.extras.models import DynamicGroup
from nautobot.extras.querysets import DynamicGroupQuerySet
from nautobot.extras.registry import registry
from nautobot.core.utils.config import get_settings_or_config


class Command(BaseCommand):
    help = "Update the member caches for all DynamicGroups."

    def handle(self, *args, **kwargs):
        """Run through all Dynamic Groups and ensure their member caches are up to date."""

        if get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT") == 0:
            self.stdout.write(
                self.style.NOTICE("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT is set to 0; skipping cache refresh")
            )
        else:
            self.stdout.write(self.style.NOTICE("Refreshing DynamicGroup member caches..."))

        for app_label in registry["model_features"]["dynamic_groups"]:
            for model_name in registry["model_features"]["dynamic_groups"][app_label]:
                model = apps.get_model(app_label=app_label, model_name=model_name)
                cache.delete(DynamicGroupQuerySet._get_eligible_dynamic_groups_cache_key(model))

        dynamic_groups = DynamicGroup.objects.all()

        for dynamic_group in dynamic_groups:
            dynamic_group.update_cached_members()
