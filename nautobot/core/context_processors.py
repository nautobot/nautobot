from urllib.parse import urlparse

from django.conf import settings as django_settings
from django.urls import NoReverseMatch, reverse

from nautobot.core.settings_funcs import sso_auth_enabled
from nautobot.core.templatetags.helpers import has_one_or_more_perms
from nautobot.core.utils import lookup
from nautobot.extras.registry import registry


def get_saml_idp():
    """
    Context function to provide a query string for the first IDP configured for SAML.

    If the configured SAML IDP is `google`, this returns `idp=google`.

    If SAML is not configured, this returns an empty string.
    """

    idp_map = getattr(django_settings, "SOCIAL_AUTH_SAML_ENABLED_IDPS", None)

    # We will only retrieve the first and only IDP defined as we cannot support
    # more than a single IDP for SAML at this time until we come up with a more
    # robust login system.
    value = ""
    if idp_map is not None:
        try:
            idp = next(iter(idp_map.keys()))
        except IndexError:
            pass
        else:
            value = f"idp={idp}"

    return value


def settings(request):
    """
    Expose Django settings in the template context. Example: {{ settings.DEBUG }}
    """
    root_template = "base_django.html"
    return {
        "settings": django_settings,
        "root_template": root_template,
    }


def nav_menu(request):
    """
    Expose nav menu data for navigation and global search.
    Also, indicate whether `"nautobot_version_control"` app is installed in order to render branch picker in nav menu.
    """
    has_identified_active_link = False
    related_list_view_link = None
    if request.resolver_match:
        # Try to map requested page `view_name` to a specific `model` via `lookup.get_model_for_view_name`.
        try:
            model = lookup.get_model_for_view_name(request.resolver_match.view_name)
        except ValueError:
            model = None

        # If model mapping above fails, fall back to deriving a `model` from requested page `view_class` `queryset`.
        if not model:
            view_func = request.resolver_match.func
            view_class = None
            if hasattr(view_func, "view_class"):  # Valid for generic Views
                view_class = view_func.view_class
            elif hasattr(view_func, "cls"):  # Valid for UI component framework ViewSets
                view_class = view_func.cls
            view_instance = view_class() if view_class else None
            queryset = getattr(view_instance, "queryset", None)
            model = getattr(queryset, "model", None)

        # If related `model` reference has been found, map it to a list view link.
        try:
            related_list_view_name = lookup.get_route_for_model(model, "list") if model else None
            related_list_view_link = reverse(related_list_view_name) if related_list_view_name else None
        except (NoReverseMatch, ValueError):
            pass

    nav_menu_object = {"tabs": {}}

    if htmx_current_url := request.headers.get("HX-Current-URL"):
        current_url = urlparse(htmx_current_url).path
    else:
        current_url = request.path

    for tab_name, tab_details in registry["nav_menu"]["tabs"].items():
        if not tab_details["permissions"] or has_one_or_more_perms(request.user, tab_details["permissions"]):
            nav_menu_object["tabs"][tab_name] = {"groups": {}, "icon": tab_details["icon"]}
            for group_name, group_details in tab_details["groups"].items():
                if not group_details["permissions"] or has_one_or_more_perms(
                    request.user, group_details["permissions"]
                ):
                    nav_menu_object["tabs"][tab_name]["groups"][group_name] = {"items": {}}
                    for item_link, item_details in group_details["items"].items():
                        if not item_details["permissions"] or has_one_or_more_perms(
                            request.user, item_details["permissions"]
                        ):
                            if has_identified_active_link:
                                is_active = False
                            else:
                                is_active = item_link in [current_url, related_list_view_link]
                                if is_active:
                                    has_identified_active_link = True

                            nav_menu_object["tabs"][tab_name]["groups"][group_name]["items"][item_link] = {
                                "is_active": is_active,
                                "name": item_details["name"],
                                "weight": item_details["weight"],
                            }
                    if len(nav_menu_object["tabs"][tab_name]["groups"][group_name]["items"]) == 0:
                        del nav_menu_object["tabs"][tab_name]["groups"][group_name]
            if len(nav_menu_object["tabs"][tab_name]["groups"]) == 0:
                del nav_menu_object["tabs"][tab_name]

    nav_menu_version_control = None
    if "nautobot_version_control" in django_settings.PLUGINS:
        from nautobot_version_control.utils import active_branch  # pylint: disable=import-error

        nav_menu_version_control = {"active_branch": active_branch()}

    return {"nav_menu": nav_menu_object, "nav_menu_version_control": nav_menu_version_control}


def sso_auth(request):
    """
    Expose SSO-related variables for use in generating login URL fragments for external authentication providers.
    """

    return {
        "SAML_IDP": get_saml_idp,
        "SSO_AUTH_ENABLED": lambda: sso_auth_enabled(django_settings.AUTHENTICATION_BACKENDS),
    }
