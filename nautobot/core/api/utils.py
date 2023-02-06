from collections import namedtuple
import platform
import sys

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.utils import formatting

from nautobot.core.api import exceptions


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


def dynamic_import(name):
    """
    Dynamically import a class from an absolute path string
    """
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


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


def get_serializer_for_model(model, prefix=""):
    """
    Dynamically resolve and return the appropriate serializer for a model.
    """
    app_name, model_name = model._meta.label.split(".")
    # Serializers for Django's auth models are in the users app
    if app_name == "auth":
        app_name = "users"
    serializer_name = f"{app_name}.api.serializers.{prefix}{model_name}Serializer"
    if app_name not in settings.PLUGINS:
        serializer_name = f"nautobot.{serializer_name}"
    try:
        return dynamic_import(serializer_name)
    except AttributeError:
        raise exceptions.SerializerNotFound(
            f"Could not determine serializer for {app_name}.{model_name} with prefix '{prefix}'"
        )


def is_api_request(request):
    """
    Return True of the request is being made via the REST API.
    """
    api_path = reverse("api-root")
    return request.path_info.startswith(api_path)


def get_view_name(view, suffix=None):
    """
    Derive the view name from its associated model, if it has one. Fall back to DRF's built-in `get_view_name`.
    """
    if hasattr(view, "queryset"):
        # Determine the model name from the queryset.
        name = view.queryset.model._meta.verbose_name
        name = " ".join([w[0].upper() + w[1:] for w in name.split()])  # Capitalize each word

    else:
        # Replicate DRF's built-in behavior.
        name = view.__class__.__name__
        name = formatting.remove_trailing_string(name, "View")
        name = formatting.remove_trailing_string(name, "ViewSet")
        name = formatting.camelcase_to_spaces(name)

    if suffix:
        name += " " + suffix

    return name


def rest_api_server_error(request, *args, **kwargs):
    """
    Handle exceptions and return a useful error message for REST API requests.
    """
    type_, error, _traceback = sys.exc_info()
    data = {
        "error": str(error),
        "exception": type_.__name__,
        "nautobot_version": settings.VERSION,
        "python_version": platform.python_version(),
    }
    return JsonResponse(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_model_api_endpoint(related_model):
    app_label = related_model._meta.app_label
    model_name = related_model._meta.model_name

    if app_label in settings.PLUGINS:
        data_url = reverse(f"plugins-api:{app_label}-api:{model_name}-list")
    else:
        data_url = reverse(f"{app_label}-api:{model_name}-list")
    return data_url


def format_output(field, field_value):
    data = {
        "field_name": field,  # Form field placeholder
        "type": "others",  # Param type e.g select field, char field, datetime field etc.
        "choices": [],  # Param choices for select fields
        "help_text": None,  # Form field placeholder
        "label": None,  # Form field placeholder
        "required": False,  # Form field placeholder
    }
    # choice field, char field, nested-serializer field, integer-field
    # nested serializer
    from nautobot.core.api import WritableNestedSerializer
    from rest_framework.fields import CharField
    from rest_framework.fields import IntegerField
    from rest_framework.serializers import ListSerializer
    from nautobot.core.api import ChoiceField
    from nautobot.extras.api.fields import StatusSerializerField

    kwargs = {}
    if isinstance(field_value, (WritableNestedSerializer, ListSerializer, StatusSerializerField)):
        kwargs = {
            "type": "dynamic-choice-field",
        }
        extra_kwargs = {}

        if isinstance(field_value, WritableNestedSerializer):
            extra_kwargs = {
                "label": getattr(field_value, "label", None) or field,
                "required": field_value.required,
                "help_text": field_value.help_text,
            }
        elif isinstance(field_value, ListSerializer):
            extra_kwargs = {
                "label": "Tags",
                "required": False,
            }
        elif isinstance(field_value, StatusSerializerField):
            extra_kwargs = {
                "label": "Status",
                "required": True,
            }
        kwargs.update(extra_kwargs)
    elif isinstance(field_value, ChoiceField):
        kwargs = {
            "type": "choice-field",
            "label": getattr(field_value, "label", None) or field,
            "required": field_value.required,
            "help_text": field_value.help_text,
            "choices": field_value.choices.items(),
        }
    elif isinstance(field_value, CharField):
        kwargs = {
            "type": "char-field",
            "label": getattr(field_value, "label", None) or field,
            "required": field_value.required,
            "help_text": field_value.help_text,
        }
    elif isinstance(field_value, IntegerField):
        kwargs = {
            "type": "integer-field",
            "label": getattr(field_value, "label", None) or field,
            "required": field_value.required,
            "help_text": field_value.help_text,
        }
    data.update(kwargs)
    return data


def get_data_for_serializer_parameter(model):
    serializer = get_serializer_for_model(model)
    writeable_fields = {
        field_name: format_output(field_name, field_value)
        for field_name, field_value in serializer().get_fields().items()
        if not field_value.read_only
    }
    return writeable_fields
