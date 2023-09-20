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
            r_pattern = pattern.pattern.regex.pattern.lstrip("^").rstrip(r"\Z")
            combined_pattern = prefix + r_pattern
            new_ui_routes.update(get_only_new_ui_ready_routes(pattern.url_patterns, combined_pattern))
        else:
            use_new_ui = False
            # There are two types of generic view class ObjectView and NautobotUIViewSet which has different approach to validate if this route is a new_ui_ready route
            if hasattr(pattern.callback, "view_class"):
                # For ObjectView
                use_new_ui = getattr(pattern.callback.view_class, "use_new_ui", False)
            elif hasattr(pattern.callback, "cls"):
                # For NautobotUIViewSet
                use_new_ui_list = getattr(pattern.callback.cls, "use_new_ui", [])
                # Check if the current action is part of the allowed actions in this ViewSet class
                use_new_ui = bool(set(use_new_ui_list) & set(pattern.callback.actions.values()))
            if use_new_ui:
                r_pattern = pattern.pattern.regex.pattern.lstrip("^")
                final_pattern = rf"^{prefix}{r_pattern}"
                new_ui_routes.add(final_pattern)
    return new_ui_routes


def get_all_new_ui_ready_routes():
    """"""
    resolver = get_resolver()
    url_patterns = resolver.url_patterns
    return get_only_new_ui_ready_routes(url_patterns)


def is_route_new_ui_ready(route):
    return any(re.compile(url).match(route.lstrip("/")) for url in registry["new_ui_ready_routes"])
