import copy
from importlib import import_module
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

from django.apps import apps
from django.conf import settings
from django.contrib.admindocs.views import simplify_regex
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
            help="Do not (re)render Nautobot App imports.",
        )
        parser.add_argument(
            "--no-npm-build",
            action="store_false",
            dest="npm_build",
            default=True,
            help="Do not compile UI.",
        )

    def convert_django_url_regex_to_react_route_path(self, regex):
        """
        Converts a regular expression object to its equivalent react router path representation.

        Args:
            regex (re.Pattern): A regular expression object.

        Example:
            >>> pattern = re.compile('^other-models/(?P<pk>[^/.]+)/notes/$')
            >>> convert_django_url_regex_to_react_route_path(pattern)
            '/other-models/:pk/notes/'
        """
        pattern = str(regex.pattern)
        path = simplify_regex(pattern).replace("<", ":").replace(">", "").replace("\\Z", "").replace("\\", "")
        return path if path.endswith("/") else f"{path}/"

    def get_app_component(self, file_path, route_name):
        """
        Obtains the view component for the given route name from the index.js file of the App.
        This locates the `route_name` in the app configuration `routes_view_components` dict and
        returns the View Component registered for the `route_name`.

        Parameters:
            file_path (str): The path to the JavaScript file to read from.
            route_name (str): The name of the route to extract the view component for.

        Returns:
            str: The view component associated with the specified route name, or None if not found.

        Example:
            >>> get_app_component(file_path="/src/example_plugin/example_plugin/ui/index.js", route_name="example-plugin:examplemodel_list")
            "ExampleModelListView"
        """
        try:
            with open(file_path, "r") as f:
                js_content = f.read()
        except FileNotFoundError:
            return None

        # Construct a regular expression that matches the specified key and extracts the associated view component
        pattern = rf'routes_view_components:\s*{{[^}}]*"{re.escape(route_name)}"\s*:\s*"([^"]+)"'
        view_component_match = re.search(pattern, js_content)
        return view_component_match[1] if view_component_match else None

    def render_routes_imports(self, app_base_path, app_name, app_config):
        """
        Renders the imports for the React Router components of the App's URLs.

        This method inspects the `urlpatterns` list of the `urls.py` module of the App and generates
        a list of dictionaries representing the React Router components and their corresponding URL paths.

        Args:
            app_base_path (Path): The base path of the Django app.
            app_name (str): The name of the Django app.
            app_config (AppConfig): The configuration object of the Django app.

        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the React Router components and their
            corresponding URL paths.
            Each dictionary has the following keys:
            - "path": The URL path pattern.
            - "component": The React component associated with the URL path.

        Example:
            >>> render_routes_imports("/src/example_plugin/", "example_plugin", <AppConfig instance>)
            [
                { "path": "example-plugin/", "component": "HomeView"},
                { "path": "example-plugin/config/", "component": "ConfigView"},
            ]
        """
        data = []
        try:
            module = import_module(f"{app_name}.urls")
            base_url = app_config.base_url or app_config.label
            for urlpattern in module.urlpatterns:
                if component := self.get_app_component(
                    app_base_path / "ui/index.js",
                    f"{base_url}:{urlpattern.name}",
                ):
                    path_regex = urlpattern.pattern.regex
                    url_path = self.convert_django_url_regex_to_react_route_path(path_regex)
                    data.append({"path": base_url + url_path, "component": component})
            return data
        except (AttributeError, ModuleNotFoundError):
            # If an app does not include its url.py file or urls.py does not include a urlpatterns, skip.
            return data

    def render_app_imports(self, render_apps=False):
        """
        Render dynamically constructed app-related files - `app_imports.js`, `app_routes.json`, `jsconfig.paths.json`.

        - If `render_apps` is True, these files will be regenerated according to the apps included in settings.PLUGINS.
        - If `render_apps` is False but the files do not yet exist, they will be created but will not include any apps.
        - If `render_apps` is False and the files already exist, they will be left untouched.
        """

        ui_dir = settings.NAUTOBOT_UI_DIR

        # Input files
        router_file_path = Path(ui_dir, "src", "router.js")
        jsconfig_base_file_path = Path(ui_dir, "src", "file_templates", "jsconfig-base.json")
        environment = jinja2.sandbox.SandboxedEnvironment(
            loader=jinja2.FileSystemLoader(Path(ui_dir, "src", "file_templates"))
        )
        template = environment.get_template("app_imports.js.j2")

        # Output files
        output_dir = Path(ui_dir, "generated")
        os.makedirs(output_dir, exist_ok=True)
        jsconfig_file_path = Path(output_dir, "jsconfig.paths.json")
        app_routes_file_path = Path(output_dir, "app_routes.json")
        app_imports_final_file_path = Path(output_dir, "app_imports.js")

        app_routes = {}
        with open(jsconfig_base_file_path, "r", encoding="utf-8") as base_config_file:
            jsconfig = json.load(base_config_file)

        if render_apps:
            self.stdout.write(self.style.WARNING(">>> Rendering Nautobot App imports..."))
            # We're going to modify this list if apps don't have a `ui` directory.
            enabled_apps = copy.copy(settings.PLUGINS)

            for app_class_path in settings.PLUGINS:
                app_name = app_class_path.split(".")[-1]
                app_config = apps.get_app_config(app_name)
                abs_app_path = Path(app_config.path).resolve()
                abs_app_ui_path = abs_app_path / "ui"
                app_path = Path(os.path.relpath(abs_app_path, ui_dir))
                app_ui_path = app_path / "ui"
                if app_routes_imports := self.render_routes_imports(abs_app_path, app_name, app_config):
                    app_routes[app_name] = app_routes_imports

                # Assert that an App has a UI folder.
                if not abs_app_ui_path.exists():
                    self.stdout.write(self.style.ERROR(f"    - App {app_name!r} does not publish a UI; Skipping..."))
                    enabled_apps.remove(app_class_path)
                    continue
                self.stdout.write(self.style.SUCCESS(f"    - App {app_name!r} imported"))

                jsconfig["compilerOptions"]["paths"][f"@{app_name}/*"] = [f"{app_ui_path}/*"]
        else:
            enabled_apps = []

        files_generated = False

        if render_apps or not os.path.exists(jsconfig_file_path):
            with open(jsconfig_file_path, "w", encoding="utf-8") as generated_config_file:
                json.dump(jsconfig, generated_config_file, indent=4)
            self.stdout.write(self.style.SUCCESS(f"    - Rendered {jsconfig_file_path}"))
            files_generated = True

        if render_apps or not os.path.exists(app_routes_file_path):
            with open(app_routes_file_path, "w", encoding="utf-8") as app_routes_file:
                json.dump(app_routes, app_routes_file, indent=4)
            self.stdout.write(self.style.SUCCESS(f"    - Rendered {app_routes_file_path}"))
            files_generated = True

        if render_apps or not os.path.exists(app_imports_final_file_path):
            content = template.render(apps=enabled_apps)
            with open(app_imports_final_file_path, "w", encoding="utf-8") as generated_import_file:
                generated_import_file.write(content)
            self.stdout.write(self.style.SUCCESS(f"    - Rendered {app_imports_final_file_path}"))
            files_generated = True

        if files_generated:
            # Touch the router to attempt to trigger a server reload.
            Path(router_file_path).touch()

    def run_command(self, command, message, cwd=settings.NAUTOBOT_UI_DIR):
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

        if not os.path.exists(Path(settings.NAUTOBOT_UI_DIR)):
            os.makedirs(Path(settings.NAUTOBOT_UI_DIR))

        self.run_command(
            f"cp -r {Path(settings.BASE_DIR, 'ui')}/. {Path(settings.NAUTOBOT_UI_DIR)}",
            ">>> Copying UI source files...",
        )

        # Generate `app_imports.js`, `app_routes.json`, and `jsconfig.paths.json` if necessary or if requested.
        self.render_app_imports(options["render_apps"])

        # Run `npm install` and keep it silent by default.
        if options["npm_install"]:
            args = f"install {loglevel} --no-progress"
            self.run_command(f"npm {args}", ">>> Installing Nautobot UI dependencies...")

        # Run `npm build` and keep it silent by default.
        if options["npm_build"]:
            args = f"run build {loglevel}"
            self.run_command(f"npm {args}", ">>> Compiling Nautobot UI packages...")
            self.run_command(
                f"cp {Path(settings.NAUTOBOT_UI_DIR, 'build' ,'asset-manifest.json')} "
                f"{Path(settings.NAUTOBOT_UI_DIR, 'build' , 'static', 'asset-manifest.json')}",
                ">>> Copying built manifest...",
            )

        self.stdout.write(self.style.SUCCESS(">>> Nautobot UI build complete! 🎉"))
