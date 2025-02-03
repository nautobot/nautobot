from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.utils.http import urlencode
import yaml

from nautobot.core.utils.lookup import get_model_for_view_name


class Command(BaseCommand):
    """
    Example usage: `nautobot-server generate_performance_test_endpoints > endpoints.yml`
    """

    help = "List all relevant performance test url patterns in Nautobot Core"

    def handle(self, *args, **options):
        # Get the URL resolver
        url_patterns = get_resolver().url_patterns

        # Group the urls by app names
        self.app_name_to_urls = {}
        self.app_name_to_urls["endpoints"] = {}
        # Fetch and store the urls by app names in the dictionary
        self.fetch_urls(url_patterns)
        for view_name, url_patterns in self.app_name_to_urls["endpoints"].items():
            self.app_name_to_urls["endpoints"][view_name] = sorted(list(set(url_patterns)))

        with open("./endpoints.yml", "w") as outfile:
            yaml.dump(self.app_name_to_urls, outfile, sort_keys=True)

    def is_get_endpoint(self, view_name):
        """
        Check if the view is a GET endpoint
        """
        get_endpoints_suffixes = ("-detail", "_list", "_notes", "_changelog", "-list", "-notes")
        if view_name.endswith(get_endpoints_suffixes) or "_" not in view_name:
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
        # If the model class is found, then we know we are dealing with a model related endpoint
        if model_class:
            if len(model_class.objects.all()) > 1:
                # Handle detail view url patterns
                if "_list" not in view_name and "-list" not in view_name:
                    # Identify the placeholder for the uuid
                    replace_string = ""
                    if "<uuid:pk>" in url_pattern:
                        replace_string = "<uuid:pk>"
                    elif "(?P<pk>[/.]+)" in url_pattern:
                        replace_string = "(?P<pk>[/.]+)"

                    if replace_string:
                        # Replace the uuid with the actual uuid
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
                    total_count = len(model_class.objects.all())
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
                    # One endpoint with default pagination
                    self.app_name_to_urls["endpoints"][view_name].append(url_pattern + f"?{query_params}")
            else:
                # TODO handle the case where there is no instances of the model is found
                # self.stdout.write(f"No instances of {model_class} found")
                pass
        else:
            # A generic endpoint like `core:home`
            if view_name not in self.app_name_to_urls["endpoints"]:
                self.app_name_to_urls["endpoints"][view_name] = []
            self.app_name_to_urls["endpoints"][view_name].append(url_pattern)

    def construct_view_name_and_url_pattern(self, pattern):
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
        is_plugin = lookup_str_list[0] != "nautobot"
        is_api_endpoint = False
        # Determine if the endpoint is an API endpoint
        if "api" in lookup_str_list:
            is_api_endpoint = True

        if not is_plugin:
            # One of the nautobot apps: circuits, dcim, and etc.
            app_name = lookup_str_list[1]
        else:
            # One of the plugin apps: example_app, and etc.
            app_name = lookup_str_list[0]

        model = pattern.default_args.get("model", None)
        if model:
            app_name = model._meta.app_label

        # Handle the special case first for Installed apps related view is nested under the extras app.
        # ['nautobot', 'extras', 'plugins', 'views', 'InstalledAppsView']
        if app_name == "extras" and "plugins" in lookup_str_list:
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

            return url_pattern, view_name, is_api_endpoint

        if is_api_endpoint:
            if not is_plugin:
                # One of the nautobot apps: circuits, dcim, and etc.
                url_pattern = f"/api/{app_name}/{pattern.pattern}"  # /api/dcim/devices/
                app_name = f"{app_name}-api"  # dcim-api
                view_name = f"{app_name}:{pattern.name}"  # dcim-api:device-list
            else:
                url_pattern = f"/api/plugins/{app_name}/{pattern.pattern}"  # /api/plugins/example-app/models/
                app_name = f"{app_name}-api"  # example_app-api
                view_name = f"plugins-api:{app_name}:{pattern.name}"  # plugins-api:example_app-api:examplemodel-list
        else:
            if not is_plugin:
                url_pattern = f"/{app_name}/{pattern.pattern}"  # /dcim/devices/
                view_name = f"{app_name}:{pattern.name}"  # dcim:device_list
            else:
                url_pattern = f"/plugins/{app_name}/{pattern.pattern}"  # /plugins/example-app/models/
                view_name = f"plugins:{app_name}:{pattern.name}"  # plugins:example_app:examplemodel_list

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
                    if "(?P<format>[a-z0-9]+)" not in url_pattern and self.is_get_endpoint(view_name):
                        # Replace "^" and "$" from the url pattern
                        url_pattern = url_pattern.replace("^", "").replace("$", "")
                        # Retrieve the model class for the view name
                        model_class = get_model_for_view_name(view_name)
                        self.append_urls_to_dict(url_pattern, model_class, view_name, is_api_endpoint)
