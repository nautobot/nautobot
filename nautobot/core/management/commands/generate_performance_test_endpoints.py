from django.core.management.base import BaseCommand
from django.urls import get_resolver
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
        with open("./endpoints.yml", "w") as outfile:
            yaml.dump(self.app_name_to_urls, outfile, sort_keys=True)

    def is_get_endpoint(self, view_name):
        """
        Check if the view is a GET endpoint
        """
        if view_name.endswith(("_list", "_notes", "_changelog")) or "_" not in view_name:
            return True
        return False

    def append_urls_to_dict(self, url_pattern, model_class, view_name):
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
        print(model_class)
        if model_class:
            if len(model_class.objects.all()) > 1:
                # Handle detail view url patterns
                if "_list" not in view_name:
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
                    # One endpoint with default pagination
                    self.app_name_to_urls["endpoints"][view_name].append(
                        url_pattern
                        + "?per_page="
                        + str(per_page_query_parameter)
                        + "&"
                        + "page="
                        + str(page_query_parameter)
                    )
            else:
                # TODO handle the case where there is no instances of the model is found
                self.stdout.write(f"No instances of {model_class} found")
        else:
            # A generic endpoint like `core:home`
            if view_name not in self.app_name_to_urls["endpoints"]:
                self.app_name_to_urls["endpoints"][view_name] = []
            self.app_name_to_urls["endpoints"][view_name].append(url_pattern)

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
                ...
            },
            ...
        """
        for pattern in url_patterns:
            if hasattr(pattern, "url_patterns"):
                # If it's a nested URL pattern, recursively list its URLs
                self.fetch_urls(pattern.url_patterns)
            else:
                # TODO need to include Nautobot App endpoints as well at some point
                if pattern.lookup_str.startswith(
                    (
                        "nautobot.circuits.views",
                        "nautobot.cloud.views",
                        "nautobot.core.views",
                        "nautobot.dcim.views",
                        "nautobot.extras.views",
                        "nautobot.ipam.views",
                        "nautobot.tenancy.views",
                        "nautobot.virtualization.views",
                        "nautobot.wireless.views",
                    )
                ):
                    # Only fetch urls from relevant apps
                    app_name = pattern.lookup_str.split(".")[1]
                    model = pattern.default_args.get("model", None)
                    if model:
                        app_name = model._meta.app_label

                    view_name = f"{app_name}:{pattern.name}"
                    url_pattern = f"/{app_name}/{pattern.pattern}"

                    if self.is_get_endpoint(view_name):
                        # Replace "^" and "$" from the url pattern
                        url_pattern = url_pattern.replace("^", "").replace("$", "")
                        # Retrieve the model class for the view name
                        model_class = get_model_for_view_name(view_name)
                        self.append_urls_to_dict(url_pattern, model_class, view_name)
