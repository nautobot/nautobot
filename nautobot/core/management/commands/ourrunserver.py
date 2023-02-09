# TODO: remove this file or merge it into `runserver.py`.
import os
import pathlib
import json
import jinja2

from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command as RunServerCommand

from nautobot.extras.registry import registry


class Command(RunServerCommand):
    "Testing"

    def inner_run(self, *args, **options):
        nautobot_path = pathlib.Path(__file__).parent.parent.parent.parent.parent.resolve()
        router_file_path = os.path.join(nautobot_path, "nautobot_ui", "src", "router.js")
        jsconfig_file_path = os.path.join(nautobot_path, "nautobot_ui", "jsconfig.json")
        jsconfig_base_file_path = os.path.join(nautobot_path, "nautobot_ui", "jsconfig-base.json")

        with open(jsconfig_base_file_path, "r", encoding="utf-8") as base_config_file:
            jsconfig = json.load(base_config_file)

        for plugin_path in settings.PLUGINS:
            plugin_name = plugin_path.split(".")[-1]
            app = apps.get_app_config(plugin_name)

            plugin_path = pathlib.Path(app.path).resolve()

            # TODO: Check that a plugin has a UI folder
            jsconfig["compilerOptions"]["paths"]["@"+plugin_name + "/*"] = [str(plugin_path)+"/ui/*"]



        with open(jsconfig_file_path, "w", encoding="utf-8") as generated_config_file:
            json.dump(jsconfig, generated_config_file, indent=4)

        plugin_imports_base_file_path = os.path.join(nautobot_path, "nautobot_ui", "plugin_imports.js.j2")
        plugin_imports_final_file_path = os.path.join(nautobot_path, "nautobot_ui", "src", "plugin_imports.js")

        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(nautobot_path, "nautobot_ui")))
        template = environment.get_template("plugin_imports.js.j2")

        content = template.render(plugins=settings.PLUGINS)

        with open(plugin_imports_final_file_path, "w", encoding="utf-8") as generated_import_file:
            generated_import_file.write(content)

        pathlib.Path(router_file_path).touch()

        super().inner_run(*args, **options)
