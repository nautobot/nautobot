from django.conf import settings as django_settings

from nautobot.core.settings_funcs import sso_auth_enabled


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
            idp = list(idp_map.keys())[0]
        except IndexError:
            pass
        else:
            value = f"idp={idp}"

    return value


def settings(request):
    """
    Expose Django settings in the template context. Example: {{ settings.DEBUG }}
    """

    use_new_ui = request.COOKIES.get("newui", False)

    try:
        view_class = request.resolver_match.func.view_class
        use_new_ui = use_new_ui and getattr(view_class, "use_new_ui", False)
    except AttributeError:
        # Use this method to import the view class views that inherits from
        # NautobotUIViewSet, as this views do not have the 'view_class' attribute.
        if hasattr(request, "accepted_renderer"):
            use_new_ui = use_new_ui and getattr(request.accepted_renderer, "use_new_ui", False)

    return {
        "settings": django_settings,
        "root_template": "base_react.html" if use_new_ui else "base_django.html",
    }


def sso_auth(request):
    """
    Expose SSO-related variables for use in generating login URL fragments for external authentication providers.
    """

    return {
        "SAML_IDP": get_saml_idp,
        "SSO_AUTH_ENABLED": lambda: sso_auth_enabled(django_settings.AUTHENTICATION_BACKENDS),
    }
