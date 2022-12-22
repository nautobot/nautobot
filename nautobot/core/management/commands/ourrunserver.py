import os
import pathlib

from django.apps import apps
from django.contrib.staticfiles.management.commands.runserver import Command as RunServerCommand

from nautobot.extras.registry import registry


class Command(RunServerCommand):
    "Testing"

    def inner_run(self, *args, **options):
        nautobot_path = pathlib.Path(__file__).parent.parent.parent.parent.parent.resolve()
        nautobot_ui_path = os.path.join(nautobot_path, "nautobot_ui")
        router_file_path = os.path.join(nautobot_ui_path, "src" , "router.js")

        print(registry["plugin_template_extensions"])

        super().inner_run(*args, **options)