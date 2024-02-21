from django.core.management.base import BaseCommand
from pylint import run_pylint


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "targets",
            nargs="*",
            help="Module(s) or directory(s) to evaluate",
            default=["nautobot", "tasks.py"],
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Discover Python modules and packages in the file system subtree.",
        )

    def handle(self, *args, **options):
        args = ["--verbose", *options.pop("targets")]
        if options.pop("recursive"):
            args.append("--recursive=y")
        run_pylint(args)
