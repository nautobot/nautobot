from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = "Generates a new SECRET_KEY that can be used in a project settings file."

    requires_system_checks = False

    def handle(self, *args, **options):
        return get_random_secret_key()
