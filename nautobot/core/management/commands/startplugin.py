import os

from django.conf import settings
from django.core.management.templates import TemplateCommand


class Command(TemplateCommand):
    help = (
        "Creates a Nautobot Plugin directory structure for the given app name in "
        "the current directory or optionally in the given directory."
    )
    missing_args_message = "You must provide an plugin name."

    def add_arguments(self, parser):
        default_template = os.path.join(settings.BASE_DIR, "core", "templates", "plugin_template")
        parser.add_argument("name", help="Name of the plugin.")
        parser.add_argument("directory", nargs="?", help="Optional destination directory")
        parser.add_argument("--template", default=default_template, help="The path or URL to load the template from.")
        parser.add_argument(
            "--extension",
            "-e",
            dest="extensions",
            action="append",
            default=["py"],
            help='The file extension(s) to render (default: "py"). '
            "Separate multiple extensions with commas, or use "
            "-e multiple times.",
        )
        parser.add_argument(
            "--name",
            "-n",
            dest="files",
            action="append",
            default=[],
            help="Additional file name(s) to render. Separate multiple file names "
            "with commas, or use -n multiple times.",
        )

    def handle(self, *args, **options):
        app_name = options.pop("name")
        target = options.pop("directory")
        super().handle("app", app_name, target, **options)
