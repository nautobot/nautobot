import collections

from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    """
    Example usage: `nautobot-server generate_performance_test_endpoints > endpoints.yml`
    """

    help = "List all relevant performance test url patterns in Nautobot Core"

    def handle(self, *args, **options):
        # Get the URL resolver
        url_patterns = get_resolver().url_patterns

        # Group the urls by app names
        self.app_name_to_urls = collections.defaultdict(list)
        # Fetch and store the urls by app names in the dictionary
        self.fetch_urls(url_patterns)

        # Print the urls out in .yml format
        self.stdout.write("---")
        self.stdout.write("endpoints:")
        for app, urls in self.app_name_to_urls.items():
            for url in urls:
                pattern_name, url_pattern = url  # ["dcim:location_list:", "/dcim/locations/"]
                self.stdout.write(f"  {pattern_name}")  # "dcim:location_list:"
                self.stdout.write(f"    - {url_pattern}")  # "/dcim/locations/"

    def fetch_urls(self, url_patterns):
        for pattern in url_patterns:
            if hasattr(pattern, "url_patterns"):
                # If it's a nested URL pattern, recursively list its URLs
                self.fetch_urls(pattern.url_patterns)
            else:
                # Only fetch urls from relevant apps
                app_name = pattern.lookup_str.split(".")[1]
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
                    # ["dcim:location_list:", "/dcim/locations/"]
                    # Store the urls in above format in the dictionary
                    self.app_name_to_urls[app_name].append(
                        [f"{app_name}:{pattern.name}:", f"/{app_name}/{pattern.pattern}"]
                    )
