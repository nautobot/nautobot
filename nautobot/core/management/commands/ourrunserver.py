import os
import pathlib

from django.apps import apps
from django.contrib.staticfiles.management.commands.runserver import Command as RunServerCommand

from nautobot.extras.registry import registry


class Command(RunServerCommand):
    "Testing"

    def inner_run(self, *args, **options):
        nautobot_path = pathlib.Path(__file__).parent.parent.parent.parent.parent.resolve()
        router_file_path = os.path.join(nautobot_path, "nautobot_ui", "src" , "router.js")
        pathlib.Path(router_file_path).touch()

        super().inner_run(*args, **options)