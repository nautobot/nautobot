from django.core.management.base import BaseCommand

from nautobot.extras.models import DynamicGroup
from nautobot.utilities.config import get_settings_or_config


class Command(BaseCommand):
    help = "Update the member caches for all DynamicGroups."

    def handle(self, *args, **kwargs):
        """Run through all Dynamic Groups and ensure their member caches are up to date."""

        if get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT") == 0:
            self.stdout.write(self.style.NOTICE("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT is set to 0; skipping cache refresh"))
            return

        dynamic_groups = DynamicGroup.objects.all()

        for dynamic_group in dynamic_groups:
            self.stdout.write(self.style.SUCCESS(f"Processing DynamicGroup {dynamic_group}"))
            dynamic_group.get_members(skip_cache=False, force_update_cache=True)
