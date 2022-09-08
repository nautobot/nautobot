"""Management command to quickly get Nautobot.__version__ similar to existing django version."""
from django.core.management.base import BaseCommand

from nautobot import __version__ as VERSION


class Command(BaseCommand):
    requires_system_checks = False

    def handle(self, *args, **options):
        print(VERSION)
