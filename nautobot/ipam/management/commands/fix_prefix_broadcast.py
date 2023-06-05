from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.ipam.models import Prefix


class Command(BaseCommand):
    help = "Updates Prefix.broadcast to match the correct derived value."

    def handle(self, *args, **kwargs):
        """Run through all objects and ensure they are associated with the correct custom fields."""
        with transaction.atomic():
            for prefix in Prefix.objects.all():
                if prefix.broadcast != str(prefix.prefix[-1]):
                    self.stdout.write(f"Updating {prefix} broadcast from {prefix.broadcast} to {prefix.prefix[-1]}")
                    prefix.broadcast = prefix.prefix[-1]
                    prefix.save()
