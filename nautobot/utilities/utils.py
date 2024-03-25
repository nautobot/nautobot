import copy
import datetime
import inspect
import json
import re
import uuid
from collections import OrderedDict, namedtuple
from itertools import count, groupby
from decimal import Decimal

import django_filters
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.db.models import Count, Model, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import QueryDict
from django.template import engines
from django.urls import get_resolver, URLPattern, URLResolver
from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django.utils.tree import Node
from django_filters import (
    BooleanFilter,
    DateFilter,
    DateTimeFilter,
    filters,
    TimeFilter,
    NumberFilter,
)
from django_filters.utils import verbose_lookup_expr
from taggit.managers import _TaggableManager

from nautobot.dcim.choices import CableLengthUnitChoices
from nautobot.utilities.constants import HTTP_REQUEST_META_SAFE_COPY
from nautobot.utilities.exceptions import FilterSetFieldNotFound

# Check if field name contains a lookup expr
# e.g `name__ic` has lookup expr `ic (icontains)` while `name` has no lookup expr
CONTAINS_LOOKUP_EXPR_RE = re.compile(r"(?<=__)\w+")


def csv_format(data):
    """
    Encapsulate any data which contains a comma within double quotes.
    """
    csv = []
    for value in data:
        # Represent None or False with empty string
        if value is None or value is False:
            csv.append("")
            continue

        # Convert dates to ISO format
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = value.isoformat()

        # Force conversion to string first so we can check for any commas
        if not isinstance(value, str):
            value = f"{value}"

        # Double-quote the value if it contains a comma or line break
        if "," in value or "\n" in value:
            value = value.replace('"', '""')  # Escape double-quotes
            csv.append(f'"{value}"')
        else:
            csv.append(f"{value}")

    return ",".join(csv)


def get_route_for_model(model, action, api=False):
    """
    Return the URL route name for the given model and action. Does not perform any validation.
    Supports both core and plugin routes.

    Args:
        model (models.Model, str): Class, Instance, or dotted string of a Django Model
        action (str): name of the action in the route
        api (bool): If set, return an API route.

    Returns:
        str: return the name of the view for the model/action provided.

    Examples:
        >>> get_route_for_model(Device, "list")
        "dcim:device_list"
        >>> get_route_for_model(Device, "list", api=True)
        "dcim-api:device-list"
        >>> get_route_for_model("dcim.site", "list")
        "dcim:site_list"
        >>> get_route_for_model("dcim.site", "list", api=True)
        "dcim-api:site-list"
        >>> get_route_for_model(ExampleModel, "list")
        "plugins:example_plugin:examplemodel_list"
        >>> get_route_for_model(ExampleModel, "list", api=True)
        "plugins-api:example_plugin-api:examplemodel-list"
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
    sep = "_" if not api else "-"
    viewname = f"{prefix}{sep}{action}"

    if model._meta.app_label in settings.PLUGINS:
        viewname = f"plugins{suffix}:{viewname}"

    return viewname


def hex_to_rgb(hex_str):
    """
    Map a hex string like "00ff00" to individual r, g, b integer values.
    """
    return [int(hex_str[c : c + 2], 16) for c in (0, 2, 4)]  # noqa: E203


def rgb_to_hex(r, g, b):
    """
    Map r, g, b values to a hex string.
    """
    return "%02x%02x%02x" % (r, g, b)  # pylint: disable=consider-using-f-string


def foreground_color(bg_color):
    """
    Return the ideal foreground color (black or white) for a given background color in hexadecimal RGB format.
    """
    bg_color = bg_color.strip("#")
    r, g, b = hex_to_rgb(bg_color)
    if r * 0.299 + g * 0.587 + b * 0.114 > 186:
        return "000000"
    else:
        return "ffffff"


def lighten_color(r, g, b, factor):
    """
    Make a given RGB color lighter (closer to white).
    """
    return [
        int(255 - (255 - r) * (1.0 - factor)),
        int(255 - (255 - g) * (1.0 - factor)),
        int(255 - (255 - b) * (1.0 - factor)),
    ]


def dynamic_import(name):
    """
    Dynamically import a class from an absolute path string
    """
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def count_related(model, field):
    """
    Return a Subquery suitable for annotating a child object count.
    """
    subquery = Subquery(
        model.objects.filter(**{field: OuterRef("pk")}).order_by().values(field).annotate(c=Count("*")).values("c")
    )

    return Coalesce(subquery, 0)


def is_taggable(obj):
    """
    Return True if the instance can have Tags assigned to it; False otherwise.
    """
    if hasattr(obj, "tags"):
        if issubclass(obj.tags.__class__, _TaggableManager):
            return True
    return False


def serialize_object(obj, extra=None, exclude=None):
    """
    Return a generic JSON representation of an object using Django's built-in serializer. (This is used for things like
    change logging, not the REST API.) Optionally include a dictionary to supplement the object data. A list of keys
    can be provided to exclude them from the returned dictionary. Private fields (prefaced with an underscore) are
    implicitly excluded.
    """
    json_str = serialize("json", [obj])
    data = json.loads(json_str)[0]["fields"]

    # Include custom_field_data as "custom_fields"
    if hasattr(obj, "_custom_field_data"):
        data["custom_fields"] = data.pop("_custom_field_data")

    # Include any tags. Check for tags cached on the instance; fall back to using the manager.
    if is_taggable(obj):
        tags = getattr(obj, "_tags", []) or obj.tags.all()
        data["tags"] = [tag.name for tag in tags]

    # Append any extra data
    if extra is not None:
        data.update(extra)

    # Copy keys to list to avoid 'dictionary changed size during iteration' exception
    for key in list(data):
        # Private fields shouldn't be logged in the object change
        if isinstance(key, str) and key.startswith("_"):
            data.pop(key)

        # Explicitly excluded keys
        if isinstance(exclude, (list, tuple)) and key in exclude:
            data.pop(key)

    return data


def serialize_object_v2(obj):
    """
    Return a JSON serialized representation of an object using obj's serializer.
    """
    from nautobot.core.api.exceptions import SerializerNotFound
    from nautobot.utilities.api import get_serializer_for_model

    # Try serializing obj(model instance) using its API Serializer
    try:
        serializer_class = get_serializer_for_model(obj.__class__)
        data = serializer_class(obj, context={"request": None}).data
    except SerializerNotFound:
        # Fall back to generic JSON representation of obj
        data = serialize_object(obj)

    return data


def slugify_dots_to_dashes(content):
    """Custom slugify_function - convert '.' to '-' instead of removing dots outright."""
    return slugify(content.replace(".", "-"))


def slugify_dashes_to_underscores(content):
    """Custom slugify_function - use underscores instead of dashes; resulting slug can be used as a variable name."""
    return slugify(content).replace("-", "_")


def dict_to_filter_params(d, prefix=""):
    """
    Translate a dictionary of attributes to a nested set of parameters suitable for QuerySet filtering. For example:

        {
            "name": "Foo",
            "rack": {
                "facility_id": "R101"
            }
        }

    Becomes:

        {
            "name": "Foo",
            "rack__facility_id": "R101"
        }

    And can be employed as filter parameters:

        Device.objects.filter(**dict_to_filter(attrs_dict))
    """
    params = {}
    for key, val in d.items():
        k = prefix + key
        if isinstance(val, dict):
            params.update(dict_to_filter_params(val, k + "__"))
        else:
            params[k] = val
    return params


def normalize_querydict(querydict, form_class=None):
    """
    Convert a QueryDict to a normal, mutable dictionary, preserving list values. For example,

        QueryDict('foo=1&bar=2&bar=3&baz=')

    becomes:

        {'foo': '1', 'bar': ['2', '3'], 'baz': ''}

    This function is necessary because QueryDict does not provide any built-in mechanism which preserves multiple
    values.

    A `form_class` can be provided as a way to hint which query parameters should be treated as lists.
    """
    result = {}
    if querydict:
        for key, value_list in querydict.lists():
            if len(value_list) > 1:
                # More than one value in the querydict for this key, so keep it as a list
                # TODO: we could check here and de-listify value_list if the form_class field is a single-value one?
                result[key] = value_list
            elif (
                form_class is not None
                and key in form_class.base_fields
                # ModelMultipleChoiceField is *not* itself a subclass of MultipleChoiceField, thanks Django!
                and isinstance(form_class.base_fields[key], (forms.MultipleChoiceField, forms.ModelMultipleChoiceField))
            ):
                # Even though there's only a single value in the querydict for this key, the form wants it as a list
                result[key] = value_list
            else:
                # Only a single value in the querydict for this key, and no guidance otherwise, so make it single
                result[key] = value_list[0]
    return result


def deepmerge(original, new):
    """
    Deep merge two dictionaries (new into original) and return a new dict
    """
    merged = OrderedDict(original)
    for key, val in new.items():
        if key in original and isinstance(original[key], dict) and isinstance(val, dict):
            merged[key] = deepmerge(original[key], val)
        else:
            merged[key] = val
    return merged


def to_meters(length, unit):
    """
    Convert the given length to meters.
    """
    length = int(length)
    if length < 0:
        raise ValueError("Length must be a positive integer")

    valid_units = CableLengthUnitChoices.values()
    if unit not in valid_units:
        raise ValueError(f"Unknown unit {unit}. Must be one of the following: {', '.join(valid_units)}")

    if unit == CableLengthUnitChoices.UNIT_KILOMETER:
        return length * 1000
    if unit == CableLengthUnitChoices.UNIT_METER:
        return length
    if unit == CableLengthUnitChoices.UNIT_CENTIMETER:
        return length / 100
    if unit == CableLengthUnitChoices.UNIT_MILE:
        return length * Decimal("1609.344")
    if unit == CableLengthUnitChoices.UNIT_FOOT:
        return length * Decimal("0.3048")
    if unit == CableLengthUnitChoices.UNIT_INCH:
        return length * Decimal("0.3048") * 12
    raise ValueError(f"Unknown unit {unit}. Must be 'km', 'm', 'cm', 'mi', 'ft', or 'in'.")


def render_jinja2(template_code, context):
    """
    Render a Jinja2 template with the provided context. Return the rendered content.
    """
    rendering_engine = engines["jinja"]
    template = rendering_engine.from_string(template_code)
    # For reasons unknown to me, django-jinja2 `template.render()` implicitly calls `mark_safe()` on the rendered text.
    # This is a security risk in general, especially so in our case because we're often using this function to render
    # a user-provided template and don't want to open ourselves up to script injection or similar issues.
    # There's no `mark_unsafe()` function, but concatenating a SafeString to an ordinary string (even "") suffices.
    return "" + template.render(context=context)


def prepare_cloned_fields(instance):
    """
    Compile an object's `clone_fields` list into a string of URL query parameters. Tags are automatically cloned where
    applicable.
    """
    params = []
    for field_name in getattr(instance, "clone_fields", []):
        field = instance._meta.get_field(field_name)
        field_value = field.value_from_object(instance)

        # Swap out False with URL-friendly value
        if field_value is False:
            field_value = ""

        # This is likely an m2m field
        if isinstance(field_value, list):
            for fv in field_value:
                item_value = getattr(fv, "pk", str(fv))  # pk or str()
                params.append((field_name, item_value))

        # Omit empty values
        elif field_value not in (None, ""):
            params.append((field_name, field_value))

    # Copy tags
    if is_taggable(instance):
        for tag in instance.tags.all():
            params.append(("tags", tag.pk))

    # Concatenate parameters into a URL query string
    param_string = "&".join([f"{k}={v}" for k, v in params])

    return param_string


def shallow_compare_dict(source_dict, destination_dict, exclude=None):
    """
    Return a new dictionary of the different keys. The values of `destination_dict` are returned. Only the equality of
    the first layer of keys/values is checked. `exclude` is a list or tuple of keys to be ignored.
    """
    difference = {}

    for key in destination_dict:
        if source_dict.get(key) != destination_dict[key]:
            if isinstance(exclude, (list, tuple)) and key in exclude:
                continue
            difference[key] = destination_dict[key]

    return difference


def flatten_dict(d, prefix="", separator="."):
    """
    Flatten netsted dictionaries into a single level by joining key names with a separator.

    :param d: The dictionary to be flattened
    :param prefix: Initial prefix (if any)
    :param separator: The character to use when concatenating key names
    """
    ret = {}
    for k, v in d.items():
        key = separator.join([prefix, k]) if prefix else k
        if isinstance(v, dict):
            ret.update(flatten_dict(v, prefix=key))
        else:
            ret[key] = v
    return ret


def flatten_iterable(iterable):
    """
    Flatten a nested iterable such as a list of lists, keeping strings intact.

    :param iterable: The iterable to be flattened
    :returns: generator
    """
    for i in iterable:
        if hasattr(i, "__iter__") and not isinstance(i, str):
            for j in flatten_iterable(i):
                yield j
        else:
            yield i


def array_to_string(array):
    """
    Generate an efficient, human-friendly string from a set of integers. Intended for use with ArrayField.
    For example:
        [0, 1, 2, 10, 14, 15, 16] => "0-2, 10, 14-16"
    """
    group = (list(x) for _, x in groupby(sorted(array), lambda x, c=count(): next(c) - x))
    return ", ".join("-".join(map(str, (g[0], g[-1])[: len(g)])) for g in group)


#
# Fake request object
#


class NautobotFakeRequest:
    """
    A fake request object which is explicitly defined at the module level so it is able to be pickled. It simply
    takes what is passed to it as kwargs on init and sets them as instance variables.
    """

    def __init__(self, _dict):
        self.__dict__ = _dict

    def _get_user(self):
        """Lazy lookup function for self.user."""
        if not self._cached_user:
            User = get_user_model()
            self._cached_user = User.objects.get(pk=self._user_pk)
        return self._cached_user

    def _init_user(self):
        """Set up self.user as a lazy attribute, similar to a real Django Request object."""
        self._cached_user = None
        self.user = SimpleLazyObject(self._get_user)

    def nautobot_serialize(self):
        """
        Serialize a JSON representation that is safe to pass to Celery.

        This function is called from nautobot.core.celery.NautobotKombuJSONEncoder.
        """
        data = copy.deepcopy(self.__dict__)
        # We don't want to try to pickle/unpickle or serialize/deserialize the actual User object,
        # but make sure we do store its PK so that we can look it up on-demand after being deserialized.
        user = data.pop("user")
        data.pop("_cached_user", None)
        if "_user_pk" not in data:
            data["_user_pk"] = user.pk
        return data

    @classmethod
    def nautobot_deserialize(cls, data):
        """
        Deserialize a JSON representation that is safe to pass to Celery and return a NautobotFakeRequest instance.

        This function is registered for usage by Celery in nautobot/core/celery/__init__.py
        """
        obj = cls(data)
        obj._init_user()
        return obj

    def __getstate__(self):
        """
        Implement `pickle` serialization API.

        It turns out that Celery uses pickle internally in apply_async()/send_job() even if we have configured Celery
        to use JSON for all I/O (and we do, see settings.py), so we need to support pickle and JSON both.
        """
        return self.nautobot_serialize()

    def __setstate__(self, state):
        """
        Implement `pickle` deserialization API.

        It turns out that Celery uses pickle internally in apply_async()/send_job() even if we have configured Celery
        to use JSON for all I/O (and we do, see settings.py), so we need to support pickle and JSON both.
        """
        # Generic __setstate__ behavior
        self.__dict__.update(state)
        # Set up lazy `self.user` attribute based on `state["_user_pk"]`
        self._init_user()


def copy_safe_request(request):
    """
    Copy selected attributes from a request object into a new fake request object. This is needed in places where
    thread safe pickling of the useful request data is needed.

    Note that `request.FILES` is explicitly omitted because they cannot be uniformly serialized.
    """
    meta = {
        k: request.META[k]
        for k in HTTP_REQUEST_META_SAFE_COPY
        if k in request.META and isinstance(request.META[k], str)
    }

    return NautobotFakeRequest(
        {
            "META": meta,
            "POST": request.POST,
            "GET": request.GET,
            "user": request.user,
            "path": request.path,
            "id": getattr(request, "id", None),  # UUID assigned by middleware
        }
    )


def get_model_from_name(model_name):
    """Given a full model name in dotted format (example: `dcim.model`), a model class is returned if valid.

    :param model_name: Full dotted name for a model as a string (ex: `dcim.model`)
    :type model_name: str

    :raises TypeError: If given model name is not found.

    :return: Found model.
    """
    from django.apps import apps

    try:
        return apps.get_model(model_name)
    except (ValueError, LookupError) as exc:
        raise TypeError(exc) from exc


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


def get_related_class_for_model(model, module_name, object_suffix):
    """Return the appropriate class associated with a given model matching the `module_name` and
    `object_suffix`.

    The given `model` can either be a model class, a model instance, or a dotted representation (ex: `dcim.device`).

    The object class is expected to be in the module within the application
    associated with the model and its name is expected to be `{ModelName}{object_suffix}`.

    If a matching class is not found, this will return `None`.

    Returns:
        Either the matching object class or None
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
    app_label = model._meta.app_label
    object_name = f"{model.__name__}{object_suffix}"
    object_path = f"{app_label}.{module_name}.{object_name}"
    if app_label not in settings.PLUGINS:
        object_path = f"nautobot.{object_path}"

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

    Returns:
        Either the `FilterSet` class or `None`
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
        Either the `Form` class or `None`
    """
    object_suffix = f"{form_prefix}Form"
    return get_related_class_for_model(model, module_name="forms", object_suffix=object_suffix)


def get_table_for_model(model):
    """Return the `Table` class associated with a given `model`.

    The `Table` class is expected to be in the `tables` module within the application
    associated with the model and its name is expected to be `{ModelName}Table`.

    If a matching `Table` is not found, this will return `None`.

    Returns:
        Either the `Table` class or `None`
    """
    return get_related_class_for_model(model, module_name="tables", object_suffix="Table")


def get_url_patterns(urlconf=None, patterns_list=None, base_path="/"):
    """
    Recursively yield a list of registered URL patterns.

    Args:
        urlconf (URLConf): Python module such as `nautobot.core.urls`.
            Default if unspecified is the value of `settings.ROOT_URLCONF`, i.e. the `nautobot.core.urls` module.
        patterns_list (list): Used in recursion. Generally can be omitted on initial call.
            Default if unspecified is the `url_patterns` attribute of the given `urlconf` module.
        base_path (str): String to prepend to all URL patterns yielded.
            Default if unspecified is the string `"/"`.

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
        >>> for url_pattern in get_url_patterns(example_urls, base_path="/plugins/example-plugin/"):
        ...     print(url_pattern)
        ...
        /plugins/example-plugin/
        /plugins/example-plugin/config/
        /plugins/example-plugin/models/<uuid:pk>/dynamic-groups/
        /plugins/example-plugin/other-models/<uuid:pk>/dynamic-groups/
        /plugins/example-plugin/docs/
        /plugins/example-plugin/circuits/<uuid:pk>/example-plugin-tab/
        /plugins/example-plugin/devices/<uuid:pk>/example-plugin-tab-1/
        /plugins/example-plugin/devices/<uuid:pk>/example-plugin-tab-2/
        /plugins/example-plugin/override-target/
        /plugins/example-plugin/^models/$
        /plugins/example-plugin/^models/add/$
        /plugins/example-plugin/^models/import/$
        /plugins/example-plugin/^models/edit/$
        /plugins/example-plugin/^models/delete/$
        /plugins/example-plugin/^models/all-names/$
        /plugins/example-plugin/^models/(?P<pk>[^/.]+)/$
        /plugins/example-plugin/^models/(?P<pk>[^/.]+)/delete/$
        /plugins/example-plugin/^models/(?P<pk>[^/.]+)/edit/$
        /plugins/example-plugin/^models/(?P<pk>[^/.]+)/changelog/$
        /plugins/example-plugin/^models/(?P<pk>[^/.]+)/notes/$
        /plugins/example-plugin/^other-models/$
        /plugins/example-plugin/^other-models/add/$
        /plugins/example-plugin/^other-models/edit/$
        /plugins/example-plugin/^other-models/delete/$
        /plugins/example-plugin/^other-models/(?P<pk>[^/.]+)/$
        /plugins/example-plugin/^other-models/(?P<pk>[^/.]+)/delete/$
        /plugins/example-plugin/^other-models/(?P<pk>[^/.]+)/edit/$
        /plugins/example-plugin/^other-models/(?P<pk>[^/.]+)/changelog/$
        /plugins/example-plugin/^other-models/(?P<pk>[^/.]+)/notes/$
    """
    if urlconf is None:
        urlconf = settings.ROOT_URLCONF
    if patterns_list is None:
        patterns_list = get_resolver(urlconf).url_patterns

    for item in patterns_list:
        if isinstance(item, URLPattern):
            yield base_path + str(item.pattern)
        elif isinstance(item, URLResolver):
            # Recurse!
            yield from get_url_patterns(urlconf, item.url_patterns, base_path + str(item.pattern))


def get_url_for_url_pattern(url_pattern):
    """
    Given a URL pattern, construct a URL string that would match that pattern.

    Examples:
        >>> get_url_for_url_pattern("/plugins/example-plugin/^models/(?P<pk>[^/.]+)/$")
        '/plugins/example-plugin/models/00000000-0000-0000-0000-000000000000/'
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


# Setup UtilizationData named tuple for use by multiple methods
UtilizationData = namedtuple("UtilizationData", ["numerator", "denominator"])

# namedtuple accepts versions(list of API versions) and serializer(Related Serializer for versions).
SerializerForAPIVersions = namedtuple("SerializersVersions", ("versions", "serializer"))


def get_api_version_serializer(serializer_choices, api_version):
    """Returns the serializer of an api_version

    Args:
        serializer_choices (tuple): list of SerializerVersions
        api_version (str): Request API version

    Returns:
        returns the serializer for the api_version if found in serializer_choices else None
    """
    for versions, serializer in serializer_choices:
        if api_version in versions:
            return serializer
    return None


def versioned_serializer_selector(obj, serializer_choices, default_serializer):
    """Returns appropriate serializer class depending on request api_version, brief and swagger_fake_view

    Args:
        obj (ViewSet instance):
        serializer_choices (tuple): Tuple of SerializerVersions
        default_serializer (Serializer): Default Serializer class
    """
    if not obj.brief and not getattr(obj, "swagger_fake_view", False) and hasattr(obj.request, "major_version"):
        api_version = f"{obj.request.major_version}.{obj.request.minor_version}"
        serializer = get_api_version_serializer(serializer_choices, api_version)
        if serializer is not None:
            return serializer
    return default_serializer


def is_uuid(value):
    try:
        if isinstance(value, uuid.UUID) or uuid.UUID(value):
            return True
    except (ValueError, TypeError, AttributeError):
        pass
    return False


def pretty_print_query(query):
    """
    Given a `Q` object, display it in a more human-readable format.

    Args:
        query (Q): Query to display.

    Returns:
        str: Pretty-printed query logic

    Example:
        >>> print(pretty_print_query(Q))
        (
          site__slug='ams01' OR site__slug='bkk01' OR (
            site__slug='can01' AND status__slug='active'
          ) OR (
            site__slug='del01' AND (
              NOT (site__slug='del01' AND status__slug='decommissioning')
            )
          )
        )
    """

    def pretty_str(self, node=None, depth=0):
        """Improvement to default `Node.__str__` with a more human-readable style."""
        template = f"(\n{'  ' * (depth + 1)}"
        if self.negated:
            template += "NOT (%s)"
        else:
            template += "%s"
        template += f"\n{'  ' * depth})"
        children = []

        # If we don't have a node, we are the node!
        if node is None:
            node = self

        # Iterate over children. They will be either a Q object (a Node subclass) or a 2-tuple.
        for child in node.children:
            # Trust that we can stringify the child if it is a Node instance.
            if isinstance(child, Node):
                children.append(pretty_str(child, depth=depth + 1))
            # If a 2-tuple, stringify to key=value
            else:
                key, value = child
                children.append(f"{key}={value!r}")

        return template % (f" {self.connector} ".join(children))

    # Use pretty_str() as the string generator vs. just stringify the `Q` object.
    return pretty_str(query)


def build_lookup_label(field_name, _verbose_name):
    """
    Return lookup expr with its verbose name

    Args:
        field_name (str): Field name e.g slug__iew
        _verbose_name (str): The verbose name for the lookup exper which is suffixed to the field name e.g iew -> iendswith

    Examples:
        >>> build_lookup_label("slug__iew", "iendswith")
        >>> "ends-with (iew)"
    """
    verbose_name = verbose_lookup_expr(_verbose_name) or "exact"
    label = ""
    if not ("__destination" in field_name or "__source" in field_name):
        search = CONTAINS_LOOKUP_EXPR_RE.search(field_name)
        if search:
            label = f" ({search.group()})"

    verbose_name = "not " + verbose_name if label.startswith(" (n") else verbose_name

    return verbose_name + label


def get_all_lookup_expr_for_field(model, field_name):
    """
    Return all lookup expressions for `field_name` in `model` filterset
    """
    filterset = get_filterset_for_model(model)().filters

    if not filterset.get(field_name):
        raise FilterSetFieldNotFound("field_name not found")

    if field_name.startswith("has_"):
        return [{"id": field_name, "name": "exact"}]

    lookup_expr_choices = []

    for name, field in filterset.items():
        # remove the lookup_expr from field_name e.g name__iew -> name
        if re.sub(r"__\w+", "", name) == field_name and not name.startswith("has_"):
            lookup_expr_choices.append(
                {
                    "id": name,
                    "name": build_lookup_label(name, field.lookup_expr),
                }
            )
        elif name == field_name and not name.startswith("has_"):
            lookup_expr_choices.append(
                {
                    "id": name,
                    "name": "exact",
                }
            )

    return lookup_expr_choices


def get_filterset_field(filterset, field_name):
    field = filterset.filters.get(field_name)
    if field is None:
        raise FilterSetFieldNotFound(f"{field_name} is not a valid {type(filterset).__name__} field")
    return field


def get_filterset_parameter_form_field(model, parameter, filterset=None):
    """
    Return the relevant form field instance for a filterset parameter e.g DynamicModelMultipleChoiceField, forms.IntegerField e.t.c
    """
    # Avoid circular import
    from nautobot.extras.filters import ContentTypeMultipleChoiceFilter, CustomFieldFilterMixin, StatusFilter
    from nautobot.extras.models import Status, Tag
    from nautobot.extras.utils import ChangeLoggedModelsQuery, TaggableClassesQuery
    from nautobot.utilities.forms import (
        BOOLEAN_CHOICES,
        DatePicker,
        DateTimePicker,
        DynamicModelMultipleChoiceField,
        StaticSelect2,
        StaticSelect2Multiple,
        TimePicker,
        MultipleContentTypeField,
    )
    from nautobot.utilities.forms.widgets import (
        MultiValueCharInput,
    )

    if filterset is None or filterset.Meta.model != model:
        filterset = get_filterset_for_model(model)()
    field = get_filterset_field(filterset, parameter)
    form_field = field.field

    # TODO(Culver): We are having to replace some widgets here because multivalue_field_factory that generates these isn't smart enough
    if isinstance(field, CustomFieldFilterMixin):
        form_field = field.custom_field.to_form_field()
    elif isinstance(field, NumberFilter):
        form_field = forms.IntegerField()
    elif isinstance(field, filters.ModelMultipleChoiceFilter):
        related_model = Status if isinstance(field, StatusFilter) else field.extra["queryset"].model
        form_attr = {
            "queryset": related_model.objects.all(),
            "to_field_name": field.extra.get("to_field_name", "id"),
        }
        # Status and Tag api requires content_type, to limit result to only related content_types
        if related_model in [Status, Tag]:
            form_attr["query_params"] = {"content_types": model._meta.label_lower}

        form_field = DynamicModelMultipleChoiceField(**form_attr)
    elif isinstance(field, ContentTypeMultipleChoiceFilter):
        # While there are other objects using `ContentTypeMultipleChoiceFilter`, the case where
        # models that have sucha  filter and the `verbose_name_plural` has multiple words is ony one: "dynamic groups".
        plural_name = slugify_dashes_to_underscores(model._meta.verbose_name_plural)
        # Cable-connectable models use "cable_terminations", not "cables", as the feature name
        if plural_name == "cables":
            plural_name == "cable_terminations"
        try:
            form_field = MultipleContentTypeField(choices_as_strings=True, feature=plural_name)
        except KeyError:
            # `MultipleContentTypeField` employs `registry["model features"][feature]`, which may
            # result in an error if `feature` is not found in the `registry["model features"]` dict.
            # In this case use queryset
            queryset_map = {"tags": TaggableClassesQuery, "job_hooks": ChangeLoggedModelsQuery}
            form_field = MultipleContentTypeField(
                choices_as_strings=True, queryset=queryset_map[plural_name]().as_queryset()
            )
    elif isinstance(field, (filters.MultipleChoiceFilter, filters.ChoiceFilter)) and "choices" in field.extra:
        form_field = forms.MultipleChoiceField(choices=field.extra.get("choices"), widget=StaticSelect2Multiple)
    elif isinstance(field, (BooleanFilter,)):  # Yes / No choice
        form_field = forms.ChoiceField(choices=BOOLEAN_CHOICES, widget=StaticSelect2)
    elif isinstance(field, DateTimeFilter):
        form_field.widget = DateTimePicker()
    elif isinstance(field, DateFilter):
        form_field.widget = DatePicker()
    elif isinstance(field, TimeFilter):
        form_field.widget = TimePicker()
    elif isinstance(field, django_filters.UUIDFilter):
        form_field.widget = MultiValueCharInput()

    form_field.required = False
    form_field.initial = None
    form_field.widget.attrs.pop("required", None)

    css_classes = form_field.widget.attrs.get("class", "")
    form_field.widget.attrs["class"] = "form-control " + css_classes
    return form_field


def convert_querydict_to_factory_formset_acceptable_querydict(request_querydict, filterset):
    """
    Convert request QueryDict/GET into an acceptable factory formset QueryDict
    while discarding `querydict` params which are not part of `filterset_class` params

    Args:
        request_querydict (QueryDict): QueryDict to convert
        filterset_class: Filterset class

    Examples:
        >>> convert_querydict_to_factory_formset_acceptable_querydict({"status": ["active", "decommissioning"], "name__ic": ["site"]},)
        >>> {
        ...     'form-TOTAL_FORMS': [3],
        ...     'form-INITIAL_FORMS': ['0'],
        ...     'form-MIN_NUM_FORMS': [''],
        ...     'form-MAX_NUM_FORMS': [''],
        ...     'form-0-lookup_field': ['status'],
        ...     'form-0-lookup_type': ['status'],
        ...     'form-0-value': ['active', 'decommissioning'],
        ...     'form-1-lookup_field': ['name'],
        ...     'form-1-lookup_type': ['name__ic'],
        ...     'form-1-value': ['site']
        ... }
    """
    query_dict = QueryDict(mutable=True)
    filterset_class_fields = filterset.filters.keys()

    query_dict.setdefault("form-INITIAL_FORMS", 0)
    query_dict.setdefault("form-MIN_NUM_FORMS", 0)
    query_dict.setdefault("form-MAX_NUM_FORMS", 100)

    lookup_field_placeholder = "form-%d-lookup_field"
    lookup_type_placeholder = "form-%d-lookup_type"
    lookup_value_placeholder = "form-%d-lookup_value"

    num = 0
    request_querydict = request_querydict.copy()
    request_querydict.pop("q", None)
    for filter_field_name, value in request_querydict.items():
        # Discard fields without values
        if value:
            if filter_field_name in filterset_class_fields:
                if hasattr(filterset.filters[filter_field_name], "relationship"):
                    lookup_field = filter_field_name
                else:
                    # convert_querydict_to_factory_formset_acceptable_querydict expects to have a QueryDict as input
                    # which means we may not have the exact field name as defined in the filterset class
                    # it may contain a lookup expression (e.g. `name__ic`), so we need to strip it
                    # this is so we can select the correct field in the formset for the "field" column
                    # TODO: Since we likely need to instantiate the filterset class early in the request anyway
                    # the filterset can handle the QueryDict conversion and we can just pass the QueryDict to the filterset
                    # then use the FilterSet to de-dupe the field names
                    lookup_field = re.sub(r"__\w+", "", filter_field_name)
                lookup_value = request_querydict.getlist(filter_field_name)

                query_dict.setlistdefault(lookup_field_placeholder % num, [lookup_field])
                query_dict.setlistdefault(lookup_type_placeholder % num, [filter_field_name])
                query_dict.setlistdefault(lookup_value_placeholder % num, lookup_value)
                num += 1

    query_dict.setdefault("form-TOTAL_FORMS", max(num, 3))
    return query_dict


def is_single_choice_field(filterset, field_name):
    # Some filter parameters do not accept multiple values, e.g DateTime, Boolean, Int fields and the q field, etc.
    field = get_filterset_field(filterset, field_name)
    return not isinstance(field, django_filters.MultipleChoiceFilter)


def get_filterable_params_from_filter_params(filter_params, non_filter_params, filterset):
    """
    Remove any `non_filter_params` and fields that are not a part of the filterset from  `filter_params`
    to return only queryset filterable parameters.

    Args:
        filter_params(QueryDict): Filter param querydict
        non_filter_params(list): Non queryset filterable params
        filterset_class: The FilterSet class
    """
    for non_filter_param in non_filter_params:
        filter_params.pop(non_filter_param, None)

    # Some FilterSet field only accept single choice not multiple choices
    # e.g datetime field, bool fields etc.
    final_filter_params = {}
    for field in filter_params.keys():
        if filter_params.get(field):
            # `is_single_choice_field` implements `get_filterset_field`, which throws an exception if a field is not found.
            # If an exception is thrown, instead of throwing an exception, set `_is_single_choice_field` to 'False'
            # because the fields that were not discovered are still necessary.
            try:
                _is_single_choice_field = is_single_choice_field(filterset, field)
            except FilterSetFieldNotFound:
                _is_single_choice_field = False

            final_filter_params[field] = (
                filter_params.get(field) if _is_single_choice_field else filter_params.getlist(field)
            )

    return final_filter_params


def ensure_content_type_and_field_name_inquery_params(query_params):
    """Ensure that the `query_params` include `content_type` and `field_name` and that
    `content_type` is a valid ContentType value.
    ensure_content_type_and_field_name_inquery_params

    Return the 'ContentTypes' model and 'field_name' if validation was successful.
    """
    if "content_type" not in query_params or "field_name" not in query_params:
        raise ValidationError("content_type and field_name are required parameters", code=400)
    contenttype = query_params.get("content_type")
    app_label, model_name = contenttype.split(".")
    try:
        model_contenttype = ContentType.objects.get(app_label=app_label, model=model_name)
        model = model_contenttype.model_class()
        if model is None:
            raise ValidationError(f"model for content_type: <{model_contenttype}> not found", code=500)
    except ContentType.DoesNotExist:
        raise ValidationError("content_type not found", code=404)
    field_name = query_params.get("field_name")

    return field_name, model
