from django.core.management.base import BaseCommand
from pylint import run_pylint


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "targets",
            nargs="*",
            help="Module(s) or directory(s) to evaluate",
            default=["nautobot", "examples", "development", "tasks.py"],
        )

    def handle(self, *args, **options):
        run_pylint(["--verbose"] + options.pop("targets"))
