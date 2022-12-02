import json
import os

from django.core.management.base import BaseCommand


class BG_COLORS:
    """BG colors for terminal"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Command(BaseCommand):
    help = "Init Nautobot UI project in current plugin root directory."

    def add_arguments(self, parser):
        parser.add_argument("plugin_name", type=str, help="Plugin project name.")

    def handle(self, *args, **options):
        """
        Steps
        - Get the plugin name
        - Use this name with a suffix _ui to create the react folder
        - Then create the rest folders [components, utils, views] and file plugin-config.json
        - Add the plugin ui name to jsconfig using the directory as alias
        """

        plugin_root_dir = os.getcwd()
        plugin_name = options["plugin_name"]
        plugin_path = os.path.join(plugin_root_dir, plugin_name)
        plugin_ui_dir_name = plugin_name + "_ui"
        plugin_ui_name = "-".join(plugin_ui_dir_name.split("_"))

        try:
            os.mkdir(plugin_ui_dir_name)
            os.chdir(plugin_ui_dir_name)

            nautobot_ui_dirs = ["components", "utils", "views"]
            for dir_name in nautobot_ui_dirs:
                os.mkdir(dir_name)

            with open("plugin-config.json", "w") as file:
                # file.writelines({"d": ""})
                pass

            # Add package.json to plugin ui root
            nautobot_ui_config = {
                "name": plugin_ui_name,
                "version": "0.1.0",
                "private": True

            }
            with open("package.json", "w") as file:
                file.write(json.dumps((nautobot_ui_config)))
                pass


        except FileExistsError:
            self.stdout.write(BG_COLORS.FAIL + "Project already initialized" + BG_COLORS.ENDC)
