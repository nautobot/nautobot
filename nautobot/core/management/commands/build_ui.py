import copy
import json
import os
from pathlib import Path
import shlex
import subprocess

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import jinja2


class Command(BaseCommand):

    help = "Build the user interface for the Nautobot server environment and installed Nautobot Apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--npm-install",
            action="store_true",
            dest="npm_install",
            default=False,
            help="Install UI packages.",
        )
        parser.add_argument(
            "--no-render-apps",
            action="store_false",
            dest="render_apps",
            default=True,
            help="Do not render Nautobot App imports.",
        )
        parser.add_argument(
            "--no-npm-build",
            action="store_false",
            dest="npm_build",
            default=True,
            help="Do not compile UI.",
        )
        parser.add_argument(
            "--allow-ui-build-failure",
            action="store_true",
            dest="allow_ui_build_failure",
            default=True,
            help="Allow build errors in development (UI may fail to build)",
        )

    def render_app_imports(self):
        """Render `app_imports.js` and update `jsconfig.json` to map to the path for each."""
        self.stdout.write(self.style.WARNING(">>> Rendering Nautobot App imports..."))

        ui_dir = settings.NAUTOBOT_UI_DIR

        router_file_path = Path(ui_dir, "src", "router.js")
        jsconfig_file_path = Path(ui_dir, "jsconfig.json")
        jsconfig_base_file_path = Path(ui_dir, "jsconfig-base.json")

        with open(jsconfig_base_file_path, "r", encoding="utf-8") as base_config_file:
            jsconfig = json.load(base_config_file)

        # We're going to modify this list if apps don't have a `ui` directory.
        enabled_apps = copy.copy(settings.PLUGINS)

        for app_class_path in settings.PLUGINS:
            app_name = app_class_path.split(".")[-1]
            app_config = apps.get_app_config(app_name)
            abs_app_path = Path(app_config.path).resolve()
            abs_app_ui_path = abs_app_path / "ui"
            app_path = Path(os.path.relpath(abs_app_path, ui_dir))
            app_ui_path = app_path / "ui"

            # Assert that an App has a UI folder.
            if not abs_app_ui_path.exists():
                self.stdout.write(self.style.ERROR(f"- App {app_name!r} does not publish a UI; Skipping..."))
                enabled_apps.remove(app_class_path)
                continue
            self.stdout.write(self.style.SUCCESS(f"- App {app_name!r} imported"))

            jsconfig["compilerOptions"]["paths"][f"@{app_name}/*"] = [f"{app_ui_path}/*"]

        with open(jsconfig_file_path, "w", encoding="utf-8") as generated_config_file:
            json.dump(jsconfig, generated_config_file, indent=4)

        app_imports_final_file_path = Path(ui_dir, "src", "app_imports.js")
        environment = jinja2.sandbox.SandboxedEnvironment(loader=jinja2.FileSystemLoader(ui_dir))
        template = environment.get_template("app_imports.js.j2")
        content = template.render(apps=enabled_apps)

        with open(app_imports_final_file_path, "w", encoding="utf-8") as generated_import_file:
            generated_import_file.write(content)

        # Touch the router to attempt to trigger a server reload.
        Path(router_file_path).touch()

    def run_command(self, command, message, cwd=settings.NAUTOBOT_UI_DIR, allow_fail=False):
        """
        Run a `command`, displaying `message` and exit. This splits it for you and runs it.

        Args:
            command (str): The command to execute
            message (str): Message to display when command is executed
        """
        self.stdout.write(self.style.WARNING(message))
        self.stdout.write(f"Running '{command}' in '{cwd}'...")

        try:
            result = subprocess.run(
                shlex.split(command),
                check=False,
                cwd=cwd,
                env={**os.environ.copy()},
                encoding="utf-8",
                capture_output=True,
            )
        except FileNotFoundError as err:
            raise CommandError(f"'{command}' failed with error: {err}")

        if result.returncode:
            self.stdout.write(self.style.NOTICE(result.stdout))
            self.stderr.write(self.style.ERROR(result.stderr))
            if not allow_fail:
                raise CommandError(f"'{command}' failed with exit code {result.returncode}")

    def handle(self, *args, **options):
        verbosity = options["verbosity"]

        # NAUTOBOT_DEBUG is also set here so that `console.log` isn't suppressed when we want
        # verbosity.
        if verbosity > 1:
            os.environ["NAUTOBOT_DEBUG"] = "1"

        verbosity_map = {
            0: "silent",
            1: "notice",
            2: "info",
            3: "silly",  # MAXIMUM OVERDEBUG
        }
        loglevel = f"--loglevel {verbosity_map[verbosity]}"

        # Generate `app_imports.js`
        if options["render_apps"]:
            self.render_app_imports()

        # Run `npm install` and keep it silent by default.
        if options["npm_install"]:
            args = f"install {loglevel} --no-progress"
            self.run_command(f"npm {args}", ">>> Installing Nautobot UI dependencies...")

        # Run `npm build` and keep it silent by default.
        if options["npm_build"]:
            args = f"run build {loglevel}"
            self.run_command(f"npm {args}", ">>> Compiling Nautobot UI packages...", allow_fail=options["allow_ui_build_failure"])
            self.run_command(
                f"cp {Path(settings.NAUTOBOT_UI_DIR, 'build' ,'asset-manifest.json')} "
                f"{Path(settings.NAUTOBOT_UI_DIR, 'build' , 'static', 'asset-manifest.json')}",
                ">>> Copying built manifest...",
                allow_fail=options["allow_ui_build_failure"],
            )

        self.stdout.write(self.style.SUCCESS(">>> Nautobot UI build complete! 🎉"))
