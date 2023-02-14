import json
import os
import pathlib
import shlex
import subprocess

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import jinja2


# TODO: Make this an absolute path relative to where the package is installed.
NAUTOBOT_UI_DIR = os.path.join(os.path.dirname(settings.BASE_DIR), "nautobot_ui")


class Command(BaseCommand):

    help = "Build user interface for Nautobot server environment and installed Nautobot Apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-npm-install",
            action="store_false",
            dest="npm_install",
            default=True,
            help="Do not install UI packages.",
        )
        parser.add_argument(
            "--no-render-plugins",
            action="store_false",
            dest="render_plugins",
            default=True,
            help="Do not render plugin imports.",
        )
        parser.add_argument(
            "--no-npm-build",
            action="store_false",
            dest="npm_build",
            default=True,
            help="Do not compile UI.",
        )

    def render_plugin_imports(self):
        """Render `plugin_imports.js` and update `jsconfig.json` to map to the path for each."""
        self.stdout.write(self.style.SUCCESS(">>> Rendering plugin imports..."))
        router_file_path = os.path.join(NAUTOBOT_UI_DIR, "src", "router.js")
        jsconfig_file_path = os.path.join(NAUTOBOT_UI_DIR, "jsconfig.json")
        jsconfig_base_file_path = os.path.join(NAUTOBOT_UI_DIR, "jsconfig-base.json")

        with open(jsconfig_base_file_path, "r", encoding="utf-8") as base_config_file:
            jsconfig = json.load(base_config_file)

        for plugin_path in settings.PLUGINS:
            plugin_name = plugin_path.split(".")[-1]
            app_config = apps.get_app_config(plugin_name)

            abs_plugin_path = pathlib.Path(app_config.path).resolve()
            plugin_path = os.path.relpath(abs_plugin_path, NAUTOBOT_UI_DIR)

            # TODO: Assert that a plugin has a UI folder.
            jsconfig["compilerOptions"]["paths"][f"@{plugin_name}/*"] = [f"{plugin_path}/ui/*"]

        with open(jsconfig_file_path, "w", encoding="utf-8") as generated_config_file:
            json.dump(jsconfig, generated_config_file, indent=4)

        plugin_imports_final_file_path = os.path.join(NAUTOBOT_UI_DIR, "src", "plugin_imports.js")

        environment = jinja2.sandbox.SandboxedEnvironment(loader=jinja2.FileSystemLoader(NAUTOBOT_UI_DIR))
        template = environment.get_template("plugin_imports.js.j2")

        content = template.render(plugins=settings.PLUGINS)

        with open(plugin_imports_final_file_path, "w", encoding="utf-8") as generated_import_file:
            generated_import_file.write(content)

        pathlib.Path(router_file_path).touch()

    def run_command(self, command, message, cwd=NAUTOBOT_UI_DIR):
        """
        Run a `command`, displaying `message` and exit. This splits it for you and runs it.

        Args:
            command (str): The command to execute
            message (str): Message to display when command is executed
        """
        self.stdout.write(self.style.SUCCESS(message))

        out = subprocess.run(
            shlex.split(command),
            cwd=cwd,
            env={**os.environ.copy()},
        )
        if out.returncode:
            raise CommandError(f"`{command}` failed with exit code {out.returncode}")

    def handle(self, **options):
        # Change to UI dir and set environment variables to be read by Webpack.
        os.environ["NAUTOBOT_STATIC_URL"] = settings.STATIC_URL
        os.environ["NAUTOBOT_STATICFILES_DIR"] = settings.STATICFILES_DIRS[0]

        # Generate `plugin_import.js`
        if options.get("render_plugins"):
            self.render_plugin_imports()

        # Try to run the build command. Make sure that if it errors, it prints
        # something like "Hey couldn't find npm, did you install it?"
        if options.get("npm_install"):
            self.run_command("npm install", ">>> Installing Nautobot dependencies...")

        if options.get("npm_build"):
            self.run_command("npm run build", ">>> Compiling Nautobot UI...")
