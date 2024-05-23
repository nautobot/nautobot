from django.core.management.base import BaseCommand

from nautobot.extras.models import DynamicGroup


class Command(BaseCommand):
    help = "Update the member caches for all DynamicGroups."

    def handle(self, *args, **kwargs):
        """Run through all Dynamic Groups and ensure their member caches are up to date."""

        self.stdout.write(self.style.NOTICE("Refreshing DynamicGroup member caches..."))

        dynamic_groups = DynamicGroup.objects.all()

        for dynamic_group in dynamic_groups:
            dynamic_group.update_cached_members()
