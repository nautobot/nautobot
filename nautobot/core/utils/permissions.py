from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


def get_permission_for_model(model, action):
    """
    Resolve the named permission for a given model (or instance) and action (e.g. view or add).

    :param model: A model or instance
    :param action: View, add, change, or delete (string)
    """
    if action not in ("view", "add", "change", "delete"):
        raise ValueError(f"Unsupported action: {action}")

    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"


def resolve_permission(name):
    """
    Given a permission name, return the app_label, action, and model_name components. For example, "dcim.view_location"
    returns ("dcim", "view", "location").

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    try:
        app_label, codename = name.split(".")
        action, model_name = codename.rsplit("_", 1)
    except ValueError:
        raise ValueError(f"Invalid permission name: {name}. Must be in the format <app_label>.<action>_<model>")

    return app_label, action, model_name


def resolve_permission_ct(name):
    """
    Given a permission name, return the relevant ContentType and action. For example, "dcim.view_location" returns
    (Location, "view").

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    app_label, action, model_name = resolve_permission(name)
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        raise ValueError(f"Unknown app_label/model_name for {name}")

    return content_type, action


def permission_is_exempt(name):
    """
    Determine whether a specified permission is exempt from evaluation.

    :param name: Permission name in the format <app_label>.<action>_<model>
    """
    app_label, action, model_name = resolve_permission(name)

    if action == "view":
        if (
            # All models (excluding those in EXEMPT_EXCLUDE_MODELS) are exempt from view permission enforcement
            "*" in settings.EXEMPT_VIEW_PERMISSIONS and (app_label, model_name) not in settings.EXEMPT_EXCLUDE_MODELS
        ) or (
            # This specific model is exempt from view permission enforcement
            f"{app_label}.{model_name}" in settings.EXEMPT_VIEW_PERMISSIONS
        ):
            return True

    return False


def qs_filter_from_constraints(constraints, tokens=None):
    """
    Construct filtered QuerySet from user constraints (tokens).

    Args:
        constraints (dict): User's permissions cached items.
        tokens (dict, optional): user tokens. Defaults to a None.

    Returns:
        QuerySet object: A QuerySet of tuples or, an empty QuerySet if constraints are null.
    """
    if tokens is None:
        tokens = {}

    def _replace_tokens(value, tokens):
        if isinstance(value, list):
            return list(map(lambda v: tokens.get(v, v), value))
        return tokens.get(value, value)

    params = Q()
    for constraint in constraints:
        if constraint:
            params |= Q(**{k: _replace_tokens(v, tokens) for k, v in constraint.items()})
        else:
            # permit model level access, constrains are null
            return Q()

    return params
