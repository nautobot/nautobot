import re
from django.urls import get_resolver

from nautobot.extras.registry import registry


def get_only_new_ui_ready_routes(patterns, prefix=""):
    """
    Recursively traverses Django URL patterns to find routes associated with view classes
    that have the `use_new_ui` attribute set to `True`.

    Args:
        patterns (list): List of URL patterns to traverse.
        prefix (str): URL pattern prefix to include when constructing route patterns.

    Returns:
        list: A list of route patterns associated with view classes that use the new UI.
    """
    new_ui_routes = set()
    for pattern in patterns:
        if hasattr(pattern, "url_patterns"):
            r_pattern = pattern.pattern.regex.pattern.lstrip("^").rstrip(
                "\Z"  # noqa: W605; invalid escape sequence '\Z'
            )
            combined_pattern = prefix + r_pattern
            new_ui_routes.update(get_only_new_ui_ready_routes(pattern.url_patterns, combined_pattern))
        elif hasattr(pattern.callback, "view_class"):
            # TODO(timizuo): Test NautobotUIViewSet routes
            if getattr(pattern.callback.view_class, "use_new_ui", None):
                r_pattern = pattern.pattern.regex.pattern.lstrip("^")
                final_pattern = rf"^{prefix}{r_pattern}"
                new_ui_routes.add(final_pattern)
    return new_ui_routes


def get_all_new_ui_ready_route():
    """"""
    resolver = get_resolver()
    url_patterns = resolver.url_patterns
    return get_only_new_ui_ready_routes(url_patterns)


def is_route_new_ui_ready(route):
    return any(re.compile(url).match(route.lstrip("/")) for url in registry["new_ui_ready_routes"])
