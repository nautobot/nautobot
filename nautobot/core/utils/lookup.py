"""Utilities for looking up related classes and information."""

import inspect
import re

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.urls import get_resolver, resolve, reverse, URLPattern, URLResolver
from django.utils.module_loading import import_string
from django.views.generic.base import RedirectView


def get_changes_for_model(model):
    """
    Return a queryset of ObjectChanges for a model or instance. The queryset will be filtered
    by the model class. If an instance is provided, the queryset will also be filtered by the instance id.
    """
    from nautobot.extras.models import ObjectChange  # prevent circular import

    if isinstance(model, Model):
        return ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(model._meta.model),
            changed_object_id=model.pk,
        )
    if issubclass(model, Model):
        return ObjectChange.objects.filter(changed_object_type=ContentType.objects.get_for_model(model._meta.model))
    raise TypeError(f"{model!r} is not a Django Model class or instance")


def get_model_from_name(model_name):
    """Given a full model name in dotted format (example: `dcim.model`), a model class is returned if valid.

    :param model_name: Full dotted name for a model as a string (ex: `dcim.model`)
    :type model_name: str

    :raises TypeError: If given model name is not found.

    :return: Found model.
    """

    try:
        return apps.get_model(model_name)
    except (ValueError, LookupError) as exc:
        raise TypeError(exc) from exc


def get_route_for_model(model, action, api=False):
    """
    Return the URL route name for the given model and action. Does not perform any validation.
    Supports both core and App routes.

    Args:
        model (models.Model, str): Class, Instance, or dotted string of a Django Model
        action (str): name of the action in the route
        api (bool): If set, return an API route.

    Returns:
        (str): return the name of the view for the model/action provided.

    Examples:
        >>> get_route_for_model(Device, "list")
        "dcim:device_list"
        >>> get_route_for_model(Device, "list", api=True)
        "dcim-api:device-list"
        >>> get_route_for_model("dcim.location", "list")
        "dcim:location_list"
        >>> get_route_for_model("dcim.location", "list", api=True)
        "dcim-api:location-list"
        >>> get_route_for_model(ExampleModel, "list")
        "plugins:example_app:examplemodel_list"
        >>> get_route_for_model(ExampleModel, "list", api=True)
        "plugins-api:example_app-api:examplemodel-list"
    """

    if isinstance(model, str):
        model = get_model_from_name(model)

    suffix = "" if not api else "-api"
    # The `contenttypes` and `auth` app doesn't provide REST API endpoints,
    # but Nautobot provides one for the ContentType model in our `extras` and Group model in `users` app.
    if model is ContentType:
        app_label = "extras"
    elif model is Group:
        app_label = "users"
    else:
        app_label = model._meta.app_label
    prefix = f"{app_label}{suffix}:{model._meta.model_name}"
    sep = ""
    if action != "":
        sep = "_" if not api else "-"
    viewname = f"{prefix}{sep}{action}"

    if apps.get_app_config(app_label).name in settings.PLUGINS:
        viewname = f"plugins{suffix}:{viewname}"

    return viewname


def get_related_class_for_model(model, module_name, object_suffix):
    """Return the appropriate class associated with a given model matching the `module_name` and
    `object_suffix`.

    The given `model` can either be a model class, a model instance, or a dotted representation (ex: `dcim.device`).

    The object class is expected to be in the module within the application
    associated with the model and its name is expected to be `{ModelName}{object_suffix}`.

    If a matching class is not found, this will return `None`.

    Args:
        model (Union[BaseModel, str]): A model class, instance, or dotted representation
        module_name (str): The name of the module to search for the object class
        object_suffix (str): The suffix to append to the model name to find the object class

    Returns:
        (Union[BaseModel, str]): Either the matching object class or None
    """
    if isinstance(model, str):
        model = get_model_from_name(model)
    if isinstance(model, Model):
        model = type(model)
    if not inspect.isclass(model):
        raise TypeError(f"{model!r} is not a Django Model class")
    if not issubclass(model, Model):
        raise TypeError(f"{model!r} is not a subclass of a Django Model class")

    # e.g. "nautobot.dcim.forms.DeviceFilterForm"
    app_config = apps.get_app_config(model._meta.app_label)
    object_name = f"{model.__name__}{object_suffix}"
    object_path = f"{app_config.name}.{module_name}.{object_name}"

    try:
        return import_string(object_path)
    # The name of the module is not correct or unable to find the desired object for this model
    except (AttributeError, ImportError, ModuleNotFoundError):
        pass

    return None


def get_filterset_for_model(model):
    """Return the `FilterSet` class associated with a given `model`.

    The `FilterSet` class is expected to be in the `filters` module within the application
    associated with the model and its name is expected to be `{ModelName}FilterSet`.

    If a matching `FilterSet` is not found, this will return `None`.

    Args:
        model (BaseModel): A model class

    Returns:
        (Union[FilterSet,None]): Either the `FilterSet` class or `None`
    """
    return get_related_class_for_model(model, module_name="filters", object_suffix="FilterSet")


def get_form_for_model(model, form_prefix=""):
    """Return the `Form` class associated with a given `model`.

    The `Form` class is expected to be in the `forms` module within the application
    associated with the model and its name is expected to be `{ModelName}{form_prefix}Form`.

    If a matching `Form` is not found, this will return `None`.

    Args:
        form_prefix (str):
            An additional prefix for the form name (e.g. `Filter`, such as to retrieve
            `FooFilterForm`) that will come after the model name.

    Returns:
        (Union[Form, None]): Either the `Form` class or `None`
    """
    object_suffix = f"{form_prefix}Form"
    return get_related_class_for_model(model, module_name="forms", object_suffix=object_suffix)


def get_related_field_for_models(from_model, to_model):
    """
    Find the field on `from_model` that is a relation to `to_model`.

    If no such field is found, returns None.
    If more than one such field is found, raises an AttributeError.

    Args:
        from_model (BaseModel): The model class that should contain the relevant field or relation.
        to_model (BaseModel): The model class that we're looking for as the destination.

    Examples:
        >>> get_related_field_for_models(Device, Location)
        <django.db.models.fields.related.ForeignKey: location>
        >>> get_related_field_for_models(Location, Device)
        <ManyToOneRel: dcim.device>
        >>> get_related_field_for_models(Prefix, Location)
        <django.db.models.fields.related.ManyToManyField: locations>
        >>> get_related_field_for_models(Location, Prefix)
        <ManyToManyRel: ipam.prefix>
        >>> get_related_field_for_models(Device, IPAddress)
        AttributeError: Device has more than one relation to IPAddress: primary_ip4, primary_ip6
    """
    matching_field = None
    for field in from_model._meta.get_fields():
        if hasattr(field, "remote_field") and field.remote_field and field.remote_field.model == to_model:
            if matching_field is not None:
                raise AttributeError(
                    f"{from_model.__name__} has more than one relation to {to_model.__name__}: "
                    f"{matching_field.name}, {field.name}"
                )
            matching_field = field
    return matching_field


def get_table_for_model(model, suffix=None):
    """Return the `Table` class associated with a given `model`.

    The `Table` class is expected to be in the `tables` module within the application
    associated with the model and its name is expected to be `{ModelName}Table`.

    If a matching `Table` is not found, this will return `None`.

    Args:
        model (BaseModel): A model class
        suffix (str): A replacement suffix for the table name (e.g. `DetailTable`, such as to retrieve `FooDetailTable`)

    Returns:
        (Union[Table, None]): Either the `Table` class or `None`
    """
    return get_related_class_for_model(model, module_name="tables", object_suffix=suffix or "Table")


def get_view_for_model(model, view_type=""):
    """Return the `UIViewSet` or `<view_type>View` class associated with a given `model`.

    The view class is expected to be in the `views` module within the app associated with the model,
    and its name is expected to be either `{ModelName}UIViewSet` or `{ModelName}{view_type}View`.

    If neither view class is found, this will return `None`.
    """
    result = get_related_class_for_model(model, module_name="views", object_suffix="UIViewSet")
    if result is None:
        result = get_related_class_for_model(model, module_name="views", object_suffix=f"{view_type}View")
    return result


def get_model_for_view_name(view_name):
    """
    Return the model class associated with the given view_name e.g. "circuits:circuit_detail", "dcim:device_list" and etc.
    If the app_label or model_name contained by the given view_name is invalid, this will return `None`.
    """
    if view_name == "users-api:group-detail":
        return Group
    if view_name == "extras-api:contenttype-detail":
        return ContentType

    split_view_name = view_name.split(":")
    if len(split_view_name) == 2:
        app_label, model_name = split_view_name  # dcim, device_list
    elif len(split_view_name) == 3:
        _, app_label, model_name = split_view_name  # plugins, app_name, model_list
    else:
        raise ValueError(f"Unexpected View Name: {view_name}")

    delimiter = "_"
    if app_label.endswith("-api"):
        app_label = app_label.replace("-api", "")
        delimiter = "-"

    model_name = model_name.split(delimiter)[0]  # device

    try:
        model = apps.get_model(app_label=app_label, model_name=model_name)
        return model
    except LookupError:
        return None


def get_table_class_string_from_view_name(view_name):
    """Return the name of the TableClass name associated with the view_name

    e.g. returns `LocationTable` for view_name `dcim:location_list`

    Args:
        view_name (String): The name of the view e.g. dcim:location_list, circuits:circuit_list

    Returns:
        table_class_name (String): The name of the model table class or None e.g. LocationTable, CircuitTable
    """

    view_func = resolve(reverse(view_name)).func
    view_class = getattr(view_func, "cls", getattr(view_func, "view_class", None))
    if hasattr(view_class, "table_class") and view_class.table_class:
        return view_class.table_class.__name__
    if hasattr(view_class, "table") and view_class.table:
        return view_class.table.__name__
    return None


def get_created_and_last_updated_usernames_for_model(instance):
    """
    Args:
        instance: A model class instance

    Returns:
        created_by: Username of the user that created the instance
        last_updated_by: Username of the user that last modified the instance
    """
    from nautobot.extras.choices import ObjectChangeActionChoices
    from nautobot.extras.models import ObjectChange

    object_change_records = get_changes_for_model(instance)
    created_by = None
    last_updated_by = None
    try:
        created_by_record = (
            object_change_records.filter(action=ObjectChangeActionChoices.ACTION_CREATE).only("user_name").first()
        )
        if created_by_record is not None:
            created_by = created_by_record.user_name
    except ObjectChange.DoesNotExist:
        pass

    last_updated_by_record = object_change_records.only("user_name").first()
    if last_updated_by_record:
        last_updated_by = last_updated_by_record.user_name

    return created_by, last_updated_by


def get_url_patterns(urlconf=None, patterns_list=None, base_path="/", ignore_redirects=False):
    """
    Recursively yield a list of registered URL patterns.

    Args:
        urlconf (URLConf): Python module such as `nautobot.core.urls`.
            Default if unspecified is the value of `settings.ROOT_URLCONF`, i.e. the `nautobot.core.urls` module.
        patterns_list (list): Used in recursion. Generally can be omitted on initial call.
            Default if unspecified is the `url_patterns` attribute of the given `urlconf` module.
        base_path (str): String to prepend to all URL patterns yielded.
            Default if unspecified is the string `"/"`.
        ignore_redirects (bool): If True, skip URL patterns that correspond to RedirectViews.

    Yields:
        (str): Each URL pattern defined in the given urlconf and its descendants

    Examples:
        >>> generator = get_url_patterns()
        >>> next(generator)
        '/'
        >>> next(generator)
        '/search/'
        >>> next(generator)
        '/login/'
        >>> next(generator)
        '/logout/'
        >>> next(generator)
        '/circuits/circuits/<uuid:pk>/terminations/swap/'

        >>> import example_plugin.urls as example_urls
        >>> for url_pattern in get_url_patterns(example_urls, base_path="/plugins/example-app/"):
        ...     print(url_pattern)
        ...
        /plugins/example-app/
        /plugins/example-app/config/
        /plugins/example-app/models/<uuid:pk>/dynamic-groups/
        /plugins/example-app/other-models/<uuid:pk>/dynamic-groups/
        /plugins/example-app/docs/
        /plugins/example-app/circuits/<uuid:pk>/example-app-tab/
        /plugins/example-app/devices/<uuid:pk>/example-app-tab-1/
        /plugins/example-app/devices/<uuid:pk>/example-app-tab-2/
        /plugins/example-app/override-target/
        /plugins/example-app/^models/$
        /plugins/example-app/^models/add/$
        /plugins/example-app/^models/import/$
        /plugins/example-app/^models/edit/$
        /plugins/example-app/^models/delete/$
        /plugins/example-app/^models/all-names/$
        /plugins/example-app/^models/(?P<pk>[^/.]+)/$
        /plugins/example-app/^models/(?P<pk>[^/.]+)/delete/$
        /plugins/example-app/^models/(?P<pk>[^/.]+)/edit/$
        /plugins/example-app/^models/(?P<pk>[^/.]+)/changelog/$
        /plugins/example-app/^models/(?P<pk>[^/.]+)/notes/$
        /plugins/example-app/^other-models/$
        /plugins/example-app/^other-models/add/$
        /plugins/example-app/^other-models/edit/$
        /plugins/example-app/^other-models/delete/$
        /plugins/example-app/^other-models/(?P<pk>[^/.]+)/$
        /plugins/example-app/^other-models/(?P<pk>[^/.]+)/delete/$
        /plugins/example-app/^other-models/(?P<pk>[^/.]+)/edit/$
        /plugins/example-app/^other-models/(?P<pk>[^/.]+)/changelog/$
        /plugins/example-app/^other-models/(?P<pk>[^/.]+)/notes/$
    """
    if urlconf is None:
        urlconf = settings.ROOT_URLCONF
    if patterns_list is None:
        patterns_list = get_resolver(urlconf).url_patterns

    for item in patterns_list:
        if isinstance(item, URLPattern):
            if (
                ignore_redirects
                and hasattr(item.callback, "view_class")
                and issubclass(item.callback.view_class, RedirectView)
            ):
                continue
            yield base_path + str(item.pattern)
        elif isinstance(item, URLResolver):
            # Recurse!
            yield from get_url_patterns(
                urlconf, item.url_patterns, base_path + str(item.pattern), ignore_redirects=ignore_redirects
            )


def get_url_for_url_pattern(url_pattern):
    """
    Given a URL pattern, construct a URL string that would match that pattern.

    Examples:
        >>> get_url_for_url_pattern("/plugins/example-app/^models/(?P<pk>[^/.]+)/$")
        '/plugins/example-app/models/00000000-0000-0000-0000-000000000000/'
        >>> get_url_for_url_pattern("/circuits/circuit-terminations/<uuid:termination_a_id>/connect/<str:termination_b_type>/")
        '/circuits/circuit-terminations/00000000-0000-0000-0000-000000000000/connect/string/'
    """
    url = url_pattern
    # Fixup tokens in path-style "classic" view URLs:
    # "/admin/users/user/<id>/password/"
    url = re.sub(r"<id>", "00000000-0000-0000-0000-000000000000", url)
    # "/silk/request/<uuid:request_id>/profile/<int:profile_id>/"
    url = re.sub(r"<int:\w+>", "1", url)
    # "/admin/admin/logentry/<path:object_id>/"
    url = re.sub(r"<path:\w+>", "1", url)
    # "/dcim/sites/<slug:slug>/"
    url = re.sub(r"<slug:\w+>", "slug", url)
    # "/apps/installed-apps/<str:app>/"
    url = re.sub(r"<str:\w+>", "string", url)
    # "/dcim/locations/<uuid:pk>/"
    url = re.sub(r"<uuid:\w+>", "00000000-0000-0000-0000-000000000000", url)
    # "/api/circuits/<drf_format_suffix:format>"
    url = re.sub(r"<drf_format_suffix:\w+>", ".json", url)
    # tokens in regexp-style router urls, including REST and NautobotUIViewSet:
    # "/extras/^external-integrations/(?P<pk>[^/.]+)/$"
    # "/api/virtualization/^interfaces/(?P<pk>[^/.]+)/$"
    # "/api/virtualization/^interfaces/(?P<pk>[^/.]+)\\.(?P<format>[a-z0-9]+)/?$"
    url = re.sub(r"[$^]", "", url)
    url = re.sub(r"/\?", "/", url)
    url = re.sub(r"\(\?P<app_label>[^)]+\)", "users", url)
    url = re.sub(r"\(\?P<class_path>[^)]+\)", "foo/bar/baz", url)
    url = re.sub(r"\(\?P<format>[^)]+\)", "json", url)
    url = re.sub(r"\(\?P<name>[^)]+\)", "string", url)
    url = re.sub(r"\(\?P<pk>[^)]+\)", "00000000-0000-0000-0000-000000000000", url)
    url = re.sub(r"\(\?P<slug>[^)]+\)", "string", url)
    url = re.sub(r"\(\?P<url>[^)]+\)", "any", url)
    # Fallthru for generic URL parameters
    url = re.sub(r"\(\?P<\w+>[^)]+\)\??", "unknown", url)
    url = re.sub(r"\\", "", url)

    if any(char in url for char in "<>[]()?+^$"):
        raise RuntimeError(f"Unhandled token in URL {url} derived from {url_pattern}")

    return url
