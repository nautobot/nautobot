from typing import Optional

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.utils.http import urlencode
import yaml

from nautobot.core.utils.lookup import get_model_for_view_name

# List of view names that are excluded for various error responses
EXCLUDED_VIEW_NAMES = [
    "graphql-api",  # "Method \\"GET\\" not allowed."
    "graphql",  # "Must provide query string."
    "dcim-api:device-napalm",  # "No platform is configured for this device."
    "dcim-api:connected-device-list",  # "Request must include \\"peer_device\\" and \\"peer_interface\\" filters."
    "login",
    "logout",
]

# List of reversed url name suffixes that are used to identify GET endpoints UI and API
GET_ENDPOINT_SUFFIXES = ("_list", "_notes", "_changelog", "-detail", "-list", "-notes")


class Command(BaseCommand):
    """
    Example usage: `nautobot-server generate_performance_test_endpoints > endpoints.yml`
    """

    help = "List all relevant performance test url patterns in Nautobot Core"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            help="A file path string that specifies the output file to write the endpoints to.",
        )

    def handle(self, *args, **options):
        # Get the URL resolver
        url_patterns = get_resolver().url_patterns

        # Group the urls by app names
        self.app_name_to_urls = {}
        self.app_name_to_urls["endpoints"] = {}
        # Fetch and store the urls by app names in the dictionary
        self.fetch_urls(url_patterns)
        for view_name, url_patterns in self.app_name_to_urls["endpoints"].items():
            # De-duplicate the URL patterns and sort them.
            self.app_name_to_urls["endpoints"][view_name] = sorted(list(set(url_patterns)))

        if filepath := options.get("output_file"):
            # Output the endpoints to a yaml file
            with open(filepath, "w") as outfile:
                yaml.dump(self.app_name_to_urls, outfile, sort_keys=True)
        else:
            # Output the endpoints to the console
            self.stdout.write(yaml.dump(self.app_name_to_urls, sort_keys=True))

    def is_eligible_get_endpoint(self, view_name):
        """
        Check if the view is a GET endpoint and if it is eligible for performance testing.
        """
        if view_name not in EXCLUDED_VIEW_NAMES and (view_name.endswith(GET_ENDPOINT_SUFFIXES) or "_" not in view_name):
            return True
        return False

    def append_urls_to_dict(self, url_pattern, model_class, view_name, is_api_endpoint=False):
        """
        URL patterns are stored in the dictionary in the following format:
            - Any model detail view URL pattern that contains `<uuid:pk>` or `(?P<pk>[/.]+)` will have two endpoints:
                - One with the `model_class.objects.first().pk`
                - One with the `model_class.objects.last().pk`
            - Any model list view URL pattern will have two endpoints:
                - One with default pagination
                - One with custom pagination (5 pages with <total_object_count//5> instances per page)
            - Any generic endpoint like `core:home` will have one endpoint which is the URL pattern itself.
        """
        if not model_class:
            # A generic endpoint like `core:home`
            if view_name not in self.app_name_to_urls["endpoints"]:
                self.app_name_to_urls["endpoints"][view_name] = []
            self.app_name_to_urls["endpoints"][view_name].append(url_pattern)
            return

        # Handle detail view url patterns
        total_count = len(model_class.objects.all())
        if "_list" not in view_name and "-list" not in view_name:
            # If the model class is found, then we know we are dealing with a model related endpoint
            if total_count == 0:
                # TODO handle the case where there is no instances of the model is found
                self.stderr.write(f"Not enough instances of {model_class} found, need at least 1")
                return

            # Identify the placeholder for the uuid
            replace_string = ""
            if "<uuid:pk>" in url_pattern:
                replace_string = "<uuid:pk>"
            elif "(?P<pk>[/.]+)" in url_pattern:
                replace_string = "(?P<pk>[/.]+)"

            if replace_string:
                # Replace the uuid with the actual uuid
                if total_count == 1:
                    # Case where there is only one instance of the model
                    first_url_pattern = url_pattern.replace(replace_string, str(model_class.objects.first().pk))
                    if view_name not in self.app_name_to_urls["endpoints"]:
                        self.app_name_to_urls["endpoints"][view_name] = []
                    self.app_name_to_urls["endpoints"][view_name].append(first_url_pattern)
                else:
                    # Case where there is more than one instance of the model
                    first_url_pattern = url_pattern.replace(replace_string, str(model_class.objects.first().pk))
                    second_url_pattern = url_pattern.replace(replace_string, str(model_class.objects.last().pk))
                    if view_name not in self.app_name_to_urls["endpoints"]:
                        self.app_name_to_urls["endpoints"][view_name] = []
                    self.app_name_to_urls["endpoints"][view_name].append(first_url_pattern)
                    self.app_name_to_urls["endpoints"][view_name].append(second_url_pattern)
        # Handle list view url patterns
        else:
            if view_name not in self.app_name_to_urls["endpoints"]:
                self.app_name_to_urls["endpoints"][view_name] = []
            # One endpoint with default pagination
            self.app_name_to_urls["endpoints"][view_name].append(url_pattern)
            page_query_parameter = 5
            per_page_query_parameter = total_count // page_query_parameter
            if not is_api_endpoint:
                query_params = urlencode(
                    {
                        "per_page": per_page_query_parameter,
                        "page": page_query_parameter,
                    }
                )
            else:
                query_params = urlencode(
                    {
                        "limit": per_page_query_parameter,
                        "offset": per_page_query_parameter * (page_query_parameter - 1),
                    }
                )
            # One endpoint with non-default pagination
            self.app_name_to_urls["endpoints"][view_name].append(url_pattern + f"?{query_params}")

    def construct_view_name_and_url_pattern(self, pattern) -> tuple[Optional[str], Optional[str], bool]:
        """
        Args:
            pattern (django.urls.resolvers.URLPattern): A URL pattern object.

        Returns:
            url_pattern (str): The URL pattern of the view.
            view_name (str): The URL name of the view.
            is_api_endpoint (bool): True if the endpoint is an API endpoint, False otherwise.
        """
        lookup_str_list = pattern.lookup_str.split(".")

        # Determine if the endpoint belongs to a plugin
        is_app = lookup_str_list[0] != "nautobot"
        is_api_endpoint = "api" in lookup_str_list
        # One of the nautobot apps: nautobot.circuits, nautobot.dcim, and etc. if not is_app
        # One of the plugins: example_app, and etc. if is_app
        app_name = lookup_str_list[0] if is_app else lookup_str_list[1]

        model = pattern.default_args.get("model", None)
        if model:
            app_name = model._meta.app_label

        # Retrieve the base URL for the app to be used in the URL pattern
        app_config = apps.get_app_config(app_name)
        base_url = app_config.base_url if hasattr(app_config, "base_url") else app_name

        if app_name == "users" and pattern.name in ["login", "logout"]:
            # No need to test the login and logout endpoints for performance testing
            url_pattern = f"/{pattern.pattern}"  # /login, /logout
            view_name = f"{pattern.name}"  # login, logout
        elif app_name == "core":
            # Handle the special case where a view exist in the core app
            # but its url pattern and view name does not include the prefix "/core" or "core:"
            # ['nautobot', 'core', "views", "HomeView"]
            # ['nautobot', 'core', "api", "views", "APIRootView"]
            if pattern.name in ["api-root", "api-status", "graphql-api"]:
                is_api_endpoint = True
                url_pattern = f"/api/{pattern.pattern}"  # /api/status
                view_name = f"{pattern.name}"  # api-status
            elif pattern.name in ["home", "about", "search", "worker-status", "graphql", "metrics"]:
                url_pattern = f"/{pattern.pattern}"  # /home, /about, /search
                view_name = f"{pattern.name}"  # home, about, search
            else:
                url_pattern = None
                view_name = None
        elif app_name == "extras" and "plugins" in lookup_str_list:
            # Handle the special case first for Installed apps related view is nested under the extras app.
            # ['nautobot', 'extras', 'plugins', 'views', 'InstalledAppsView']

            # We need special case handling to determine if the endpoint is an api endpoint as well for this view
            view_class_name = lookup_str_list[-1]
            if "API" in view_class_name:
                is_api_endpoint = True
            apps_or_plugins = "plugins" if "plugins" in pattern.name else "apps"
            if is_api_endpoint:
                url_pattern = f"/api/{apps_or_plugins}/{pattern.pattern}"  # /api/apps/installed-apps
                view_name = f"{apps_or_plugins}-api:{pattern.name}"  # apps-api:apps-list
            else:
                url_pattern = f"/{apps_or_plugins}/{pattern.pattern}"  # /apps/installed-apps
                view_name = f"{apps_or_plugins}:{pattern.name}"  # apps:apps_list
        elif is_api_endpoint:
            if not is_app:
                # One of the nautobot apps: nautobot.circuits, nautobot.dcim, and etc.
                url_pattern = f"/api/{base_url}/{pattern.pattern}"  # /api/dcim/devices/
                app_name = f"{app_name}-api"  # dcim-api
                view_name = f"{app_name}:{pattern.name}"  # dcim-api:device-list
            else:
                api_app_name = f"{app_name}-api"  # example_app-api
                view_name = (
                    f"plugins-api:{api_app_name}:{pattern.name}"  # plugins-api:example_app-api:examplemodel-list
                )
                url_pattern = f"/api/plugins/{base_url}/{pattern.pattern}"  # /api/plugins/example-app/models/
        else:
            if not is_app:
                url_pattern = f"/{base_url}/{pattern.pattern}"  # /dcim/devices/
                view_name = f"{app_name}:{pattern.name}"  # dcim:device_list
            else:
                view_name = f"plugins:{app_name}:{pattern.name}"  # plugins:example_app:examplemodel_list
                url_pattern = f"/plugins/{base_url}/{pattern.pattern}"  # /plugins/example-app/models/

        return url_pattern, view_name, is_api_endpoint

    def fetch_urls(self, url_patterns):
        """
        Store the URL patterns in the dictionary to output an .YAML file
        The dictionary will have the following structure:
        {
            "endpoints": {
                <app_name>:<view_name>: [
                    <url_pattern_1>,
                    <url_pattern_2>,
                ],
                dcim:device: [
                    "/dcim/devices/cfbd447f-d563-4fac-bb75-bdda70ab4e80/",
                    "/dcim/devices/38471bfe-0aca-4e09-b545-b0f90280fb66/",
                ],
                dcim-api:device-detail: [
                    "/api/dcim/devices/cfbd447f-d563-4fac-bb75-bdda70ab4e80/",
                    "/api/dcim/devices/38471bfe-0aca-4e09-b545-b0f90280fb66/",
                ],
                ...
            },
            ...
        """
        for pattern in url_patterns:
            if hasattr(pattern, "url_patterns"):
                # If it's a nested URL pattern, recursively list its URLs
                self.fetch_urls(pattern.url_patterns)
            else:
                # Only fetch urls from relevant apps
                if pattern.lookup_str.startswith(("nautobot.", *settings.PLUGINS)):
                    url_pattern, view_name, is_api_endpoint = self.construct_view_name_and_url_pattern(pattern)
                    # We do not need to test the ?format=<json,csv,api> endpoints and non-GET endpoints
                    if (
                        url_pattern is not None
                        and "(?P<format>[a-z0-9]+)" not in url_pattern
                        and "<drf_format_suffix:format>" not in url_pattern
                        and self.is_eligible_get_endpoint(view_name)
                    ):
                        # Replace "^" and "$" from the url pattern
                        url_pattern = url_pattern.replace("^", "").replace("$", "")
                        # Retrieve the model class for the view name
                        try:
                            model_class = get_model_for_view_name(view_name)
                        except ValueError:
                            # In case it is a generic view like /home, /about, /search
                            model_class = None
                        self.append_urls_to_dict(url_pattern, model_class, view_name, is_api_endpoint)
