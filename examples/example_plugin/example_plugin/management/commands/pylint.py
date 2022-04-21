
from django.core.management.base import BaseCommand
from pylint.lint import Run

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("module", nargs="*", help="Module(s) to evaluate", default=["nautobot"])

    def handle(self, *args, **options):
        results = Run(options.pop("module"), exit=True)
