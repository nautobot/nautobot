from collections import namedtuple
import logging
import platform
import sys

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.utils import formatting
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.model_meta import RelationInfo, _get_to_field

from nautobot.core.api import exceptions


logger = logging.getLogger(__name__)


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
    """Returns appropriate serializer class depending on request api_version, and swagger_fake_view

    Args:
        obj (ViewSet instance):
        serializer_choices (tuple): Tuple of SerializerVersions
        default_serializer (Serializer): Default Serializer class
    """
    if not getattr(obj, "swagger_fake_view", False) and hasattr(obj.request, "major_version"):
        api_version = f"{obj.request.major_version}.{obj.request.minor_version}"
        serializer = get_api_version_serializer(serializer_choices, api_version)
        if serializer is not None:
            return serializer
    return default_serializer


def get_serializer_for_model(model, prefix=""):
    """
    Dynamically resolve and return the appropriate serializer for a model.

    Raises:
        SerializerNotFound: if the requested serializer cannot be located.
    """
    app_name, model_name = model._meta.label.split(".")
    if app_name == "contenttypes" and model_name == "ContentType":
        app_name = "extras"
    # Serializers for Django's auth models are in the users app
    if app_name == "auth":
        app_name = "users"
    # Special Case where users.Permission needs ObjectPermissionSerializer
    if app_name == "users" and model_name == "Permission":
        model_name = "ObjectPermission"
    serializer_name = f"{app_name}.api.serializers.{prefix}{model_name}Serializer"
    if app_name not in settings.PLUGINS:
        serializer_name = f"nautobot.{serializer_name}"
    try:
        return dynamic_import(serializer_name)
    except AttributeError as exc:
        raise exceptions.SerializerNotFound(
            f"Could not determine serializer for {app_name}.{model_name} with prefix '{prefix}'"
        ) from exc


def get_serializers_for_models(models, prefix=""):
    """
    Dynamically resolve and return the appropriate serializers for a list of models.

    Unlike get_serializer_for_model, this will skip any models for which an appropriate serializer cannot be found,
    logging a message instead of raising the SerializerNotFound exception.

    Used primarily in OpenAPI schema generation.
    """
    serializers = []
    for model in models:
        try:
            serializers.append(get_serializer_for_model(model, prefix=prefix))
        except exceptions.SerializerNotFound as exc:
            logger.error("%s", exc)
            continue
    return serializers


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


def get_relation_info_for_nested_serializers(model_class, related_model, field_name):
    """Get the DRF RelationInfo object needed for build_nested_field()"""
    relation_info = RelationInfo(
        model_field=getattr(type(model_class), field_name),
        related_model=type(related_model),
        to_many=False,
        has_through_model=False,
        to_field=_get_to_field(getattr(type(model_class), field_name)),
        reverse=False,
    )
    return relation_info


NESTED_SERIALIZER_NAME_CACHE = {}


def get_available_nested_serializer_name(key, serializer_name):
    """
    Use a cache to keep track of used NestedSerializer names.
    Return a new NestedSerializer name for nested_serializer_factory()
    if serializer_name is taken to avoid collision in our OpenAPISchema.
    Args:
        key: The parent serializer's name
        serializer_name: Given Nested Serializer Name
    """
    # We do not use serializer name to access the cache, because serializer_name is being updated.
    if serializer_name not in NESTED_SERIALIZER_NAME_CACHE:
        NESTED_SERIALIZER_NAME_CACHE[serializer_name] = [key]
        return serializer_name
    if key != "" and key not in NESTED_SERIALIZER_NAME_CACHE[serializer_name]:
        NESTED_SERIALIZER_NAME_CACHE[serializer_name].append(key)
        return serializer_name

    NESTED_SERIALIZER_NAME_CACHE[serializer_name].append(key)
    serializer_name += str(len(NESTED_SERIALIZER_NAME_CACHE[serializer_name]))
    return serializer_name


def nested_serializer_factory(serializer, field_name, relation_info, nested_depth):
    """
    Return a NestedSerializer representation of a serializer field.
    This method should only be called in build_nested_field()
    in which field_name, relation_info and nested_depth are already given.
    """
    field = get_serializer_for_model(relation_info.related_model)

    class NautobotNestedSerializer(field):
        class Meta:
            model = relation_info.related_model
            depth = nested_depth - 1
            if hasattr(field.Meta, "fields"):
                fields = field.Meta.fields
            if hasattr(field.Meta, "exclude"):
                exclude = field.Meta.exclude

    # This is a very hacky way to avoid name collisions in OpenAPISchema Generations
    # The exact error output can be seen in this issue https://github.com/tfranzel/drf-spectacular/issues/90
    # Apparently drf-spectacular does not support the `?depth` argument that comes with DRF
    # So auto-generating NestedSerializers with the default class names that are the same when depth > 0
    # does not make our schema happy.
    if hasattr(serializer, "queryset") and serializer.queryset is not None:
        model_name = serializer.queryset.model._meta.model_name
    else:
        model_name = serializer.Meta.model._meta.model_name
    nested_serializer_name = (
        f"{model_name.capitalize()}{relation_info.related_model._meta.model_name.capitalize()}"
        + "NautobotNestedSerializer"
    )
    parent_name = ""
    if hasattr(serializer, "parent") and serializer.parent is not None:
        parent_name = serializer.parent.__class__.__name__
    NautobotNestedSerializer.__name__ = get_available_nested_serializer_name(parent_name, nested_serializer_name)
    field_class = NautobotNestedSerializer
    field_kwargs = get_nested_relation_kwargs(relation_info)
    return field_class, field_kwargs


def return_nested_serializer_data_based_on_depth(serializer, depth, obj, obj_related_field, obj_related_field_name):
    if obj_related_field.__class__.__name__ == "RelatedManager":
        result = []
        if depth == 0:
            result = obj_related_field.values_list("pk", flat=True)
        else:
            for entry in obj_related_field.all():
                relation_info = get_relation_info_for_nested_serializers(obj, entry, obj_related_field_name)
                field_class, field_kwargs = serializer.build_nested_field(obj_related_field_name, relation_info, depth)
                result.append(
                    field_class(entry, context={"request": serializer.context.get("request")}, **field_kwargs).data
                )
        return result
    else:
        if depth == 0:
            return obj_related_field.id
        else:
            relation_info = get_relation_info_for_nested_serializers(obj, obj_related_field, obj_related_field_name)
            field_class, field_kwargs = serializer.build_nested_field(obj_related_field_name, relation_info, depth)
            return field_class(
                obj_related_field, context={"request": serializer.context.get("request")}, **field_kwargs
            ).data
