import importlib
import json
import os

import simplejson
from django.core.management.base import BaseCommand


ROUTER_JS_DATA = """
import {{ useRoutes }} from "react-router-dom";
import Home from "{plugin_alias}/views/Home";


export default function Router() {{
    let element = useRoutes([
        {{
            path: "/",
            element: <Home />,
        }}
    ]);
    return element;
}}

"""

APP_JS_DATA = """
import Router from '{plugin_alias}/router';


export default function {plugin_component}(){{
    return <Router />
}}

"""

HOME_JS_DATA = """
import {Heading} from '@chakra-ui/react'


export default function Home(){
    return (
        <Heading>
            Welcome to Nautobot Plugin UI ❄️
        </Heading>
    )
}

"""


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
        """ser"""
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
        plugin = importlib.import_module(plugin_name)
        plugin_ui_name = plugin.config.nautobot_ui
        os.chdir(plugin_path)
        try:
            os.mkdir(plugin_ui_name)
            os.chdir(plugin_ui_name)

            nautobot_ui_dirs = ["components", "utils", "views"]
            for dir_name in nautobot_ui_dirs:
                os.mkdir(dir_name)

            # with open("plugin-config.json", "w") as file:
            #     # file.writelines({"d": ""})
            #     pass

            # Add package.json to plugin ui root
            nautobot_ui_config = {"name": plugin_ui_name, "version": "0.1.0", "private": True}
            with open("package.json", "w") as file:
                file.write(simplejson.dumps((nautobot_ui_config), indent=4))
                pass

            plugin_name_without_ui_suffix = plugin_ui_name.replace("_ui", "")
            plugin_alias = f"@{plugin_name_without_ui_suffix}"
            plugin_component = plugin_name_without_ui_suffix.replace("_", " ").title().replace(" ", "")

            # Add _app.js to plugin ui root
            with open("_app.js", "w") as file:
                data = APP_JS_DATA.format(plugin_alias=plugin_alias, plugin_component=plugin_component)
                file.write(data)

            # Add router.js to plugin ui root
            with open("router.js", "w") as file:
                data = ROUTER_JS_DATA.format(plugin_alias=plugin_alias)
                file.write(data)

            os.chdir("views")
            # Add Home.jsx to plugin ui root
            with open("Home.jsx", "w") as file:
                file.write(HOME_JS_DATA)

        except FileExistsError:
            self.stdout.write(BG_COLORS.FAIL + "Project already initialized" + BG_COLORS.ENDC)
