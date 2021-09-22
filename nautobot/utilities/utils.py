import copy
import datetime
import json
import inspect
from importlib import import_module
from collections import OrderedDict, namedtuple
from itertools import count, groupby

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers import serialize
from django.db.models import Count, OuterRef, Subquery, Model
from django.db.models.functions import Coalesce
from django.template import engines

from nautobot.dcim.choices import CableLengthUnitChoices
from nautobot.extras.utils import is_taggable
from nautobot.utilities.constants import HTTP_REQUEST_META_SAFE_COPY


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
            value = "{}".format(value)

        # Double-quote the value if it contains a comma or line break
        if "," in value or "\n" in value:
            value = value.replace('"', '""')  # Escape double-quotes
            csv.append('"{}"'.format(value))
        else:
            csv.append("{}".format(value))

    return ",".join(csv)


def hex_to_rgb(hex):
    """
    Map a hex string like "00ff00" to individual r, g, b integer values.
    """
    return [int(hex[c : c + 2], 16) for c in (0, 2, 4)]  # noqa: E203


def rgb_to_hex(r, g, b):
    """
    Map r, g, b values to a hex string.
    """
    return "%02x%02x%02x" % (r, g, b)


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


def normalize_querydict(querydict):
    """
    Convert a QueryDict to a normal, mutable dictionary, preserving list values. For example,

        QueryDict('foo=1&bar=2&bar=3&baz=')

    becomes:

        {'foo': '1', 'bar': ['2', '3'], 'baz': ''}

    This function is necessary because QueryDict does not provide any built-in mechanism which preserves multiple
    values.
    """
    return {k: v if len(v) > 1 else v[0] for k, v in querydict.lists()}


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
        raise ValueError("Unknown unit {}. Must be one of the following: {}".format(unit, ", ".join(valid_units)))

    if unit == CableLengthUnitChoices.UNIT_METER:
        return length
    if unit == CableLengthUnitChoices.UNIT_CENTIMETER:
        return length / 100
    if unit == CableLengthUnitChoices.UNIT_FOOT:
        return length * 0.3048
    if unit == CableLengthUnitChoices.UNIT_INCH:
        return length * 0.3048 * 12
    raise ValueError("Unknown unit {}. Must be 'm', 'cm', 'ft', or 'in'.".format(unit))


def render_jinja2(template_code, context):
    """
    Render a Jinja2 template with the provided context. Return the rendered content.
    """
    rendering_engine = engines["jinja"]
    template = rendering_engine.from_string(template_code)
    return template.render(context=context)


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
        if type(v) is dict:
            ret.update(flatten_dict(v, prefix=key))
        else:
            ret[key] = v
    return ret


# Taken from django.utils.functional (<3.0)
def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*args, *moreargs, **{**kwargs, **morekwargs})

    return _curried


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

    def nautobot_serialize(self):
        """
        Serialize a json representation that is safe to pass to celery
        """
        data = copy.deepcopy(self.__dict__)
        data["user"] = data["user"].pk
        return data

    @classmethod
    def nautobot_deserialize(cls, data):
        """
        Deserialize a json representation that is safe to pass to celery and return an actual instance
        """
        User = get_user_model()

        obj = cls(data)
        obj.user = User.objects.get(pk=obj.user)
        return obj


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


def get_filterset_for_model(model):
    """Return the FilterSet class associated with a given model.

    The FilterSet class is expected to be in the filters module within the application
    associated with the model and its name is expected to be {ModelName}FilterSet

    Not all models have a FilterSet defined so this function can return None as well

    Returns:
        either the filterset class or none
    """
    if not inspect.isclass(model):
        raise TypeError(f"model class {model} was passes as an instance!")
    if not issubclass(model, Model):
        raise TypeError(f"{model} is not a subclass of Django Model class")

    try:
        filterset_name = f"{model.__name__}FilterSet"
        if model._meta.app_label in settings.PLUGINS:
            return getattr(import_module(f"{model._meta.app_label}.filters"), filterset_name)
        else:
            return getattr(import_module(f"nautobot.{model._meta.app_label}.filters"), filterset_name)
    except ModuleNotFoundError:
        # The name of the module is not correct
        pass
    except AttributeError:
        # Unable to find a filterset for this model
        pass

    return None


# Setup UtilizationData named tuple for use by multiple methods
UtilizationData = namedtuple("UtilizationData", ["numerator", "denominator"])
