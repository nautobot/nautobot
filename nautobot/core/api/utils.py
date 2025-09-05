from collections import namedtuple
import logging
import platform
import sys

from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.utils import formatting
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.model_meta import _get_to_field, RelationInfo

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
        (Serializer): the serializer for the api_version if found in serializer_choices else None
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
    app_label, model_name = model._meta.label.split(".")
    if app_label == "contenttypes" and model_name == "ContentType":
        app_path = "nautobot.extras"
    # Serializers for Django's auth models are in the users app
    elif app_label == "auth":
        app_path = "nautobot.users"
    else:
        app_path = apps.get_app_config(app_label).name
    serializer_name = f"{app_path}.api.serializers.{prefix}{model_name}Serializer"
    try:
        return dynamic_import(serializer_name)
    except AttributeError as exc:
        raise exceptions.SerializerNotFound(
            f"Serializer for {app_label}.{model_name} not found, expected it at {serializer_name}"
        ) from exc


def nested_serializers_for_models(models, prefix=""):
    """
    Dynamically resolve and return the appropriate nested serializers for a list of models.

    Unlike get_serializer_for_model, this will skip any models for which an appropriate serializer cannot be found,
    logging a message instead of raising the SerializerNotFound exception.

    Used exclusively in OpenAPI schema generation.
    """
    from nautobot.core.api.serializers import BaseModelSerializer  # avoid circular import

    serializer_classes = []
    for model in models:
        try:
            serializer_classes.append(get_serializer_for_model(model, prefix=prefix))
        except exceptions.SerializerNotFound as exc:
            logger.warning("%s", exc)
            continue

    nested_serializer_classes = []
    for serializer_class in serializer_classes:
        if not issubclass(serializer_class, BaseModelSerializer):
            logger.warning(
                "Serializer class %s.%s does not inherit from nautobot.apps.api.BaseModelSerializer. "
                "This should probably be corrected.",
                serializer_class.__module__,
                serializer_class.__name__,
            )
            continue
        nested_serializer_name = f"Nested{serializer_class.__name__}"
        if nested_serializer_name in NESTED_SERIALIZER_CACHE:
            nested_serializer_classes.append(NESTED_SERIALIZER_CACHE[nested_serializer_name])
        else:

            class NautobotNestedSerializer(serializer_class):
                class Meta(serializer_class.Meta):
                    fields = ["id", "object_type", "url"]
                    exclude = None

                def get_field_names(self, declared_fields, info):
                    """Don't auto-add any other fields to the field_names!"""
                    return serializers.HyperlinkedModelSerializer.get_field_names(self, declared_fields, info)

            NautobotNestedSerializer.__name__ = nested_serializer_name
            NESTED_SERIALIZER_CACHE[nested_serializer_name] = NautobotNestedSerializer
            nested_serializer_classes.append(NautobotNestedSerializer)

    return nested_serializer_classes


def is_api_request(request):
    """
    Return True of the request is being made via the REST API.
    """
    api_path = reverse("api-root")
    return request.path_info.startswith(api_path)


def get_view_name(view):
    """
    Derive the view name from its associated model, if it has one. Fall back to DRF's built-in `get_view_name`.
    """
    if hasattr(view, "name") and view.name:
        return view.name
    elif hasattr(view, "queryset"):
        # Determine the model name from the queryset.
        if hasattr(view, "detail") and view.detail:
            name = view.queryset.model._meta.verbose_name
        else:
            name = view.queryset.model._meta.verbose_name_plural
        name = " ".join([w[0].upper() + w[1:] for w in name.split()])  # Capitalize each word

    else:
        # Replicate DRF's built-in behavior.
        name = view.__class__.__name__
        name = formatting.remove_trailing_string(name, "View")
        name = formatting.remove_trailing_string(name, "ViewSet")
        name = formatting.camelcase_to_spaces(name)

        # Suffix may be set by some Views, such as a ViewSet.
        suffix = getattr(view, "suffix", None)
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


def get_nested_serializer_depth(serializer):
    """
    Determine the correct depth value based on the request.
    This method is used mostly in SerializerMethodField where
    DRF does not automatically build a serializer for us because the field
    is not a native model field.
    """
    request = serializer.context.get("request", None)
    # If we do not have a request or request.method is not GET default depth to 0
    if not request or request.method != "GET" or not hasattr(serializer.Meta, "depth"):
        depth = 0
    else:
        depth = serializer.Meta.depth
    return depth


NESTED_SERIALIZER_CACHE = {}


def nested_serializer_factory(relation_info, nested_depth):
    """
    Return a NestedSerializer representation of a serializer field.
    This method should only be called in build_nested_field()
    in which relation_info and nested_depth are already given.
    """
    nested_serializer_name = f"Nested{nested_depth}{relation_info.related_model.__name__}"
    # If we already have built a suitable NestedSerializer we return the cached serializer.
    # else we build a new one and store it in the cache for future use.
    if nested_serializer_name in NESTED_SERIALIZER_CACHE:
        field_class = NESTED_SERIALIZER_CACHE[nested_serializer_name]
        field_kwargs = get_nested_relation_kwargs(relation_info)
    else:
        base_serializer_class = get_serializer_for_model(relation_info.related_model)

        class NautobotNestedSerializer(base_serializer_class):
            class Meta(base_serializer_class.Meta):
                is_nested = True
                depth = nested_depth - 1

        NautobotNestedSerializer.__name__ = nested_serializer_name
        NESTED_SERIALIZER_CACHE[nested_serializer_name] = NautobotNestedSerializer
        field_class = NautobotNestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)
    return field_class, field_kwargs


def return_nested_serializer_data_based_on_depth(serializer, depth, obj, obj_related_field, obj_related_field_name):
    """
    Handle serialization of GenericForeignKey fields at an appropriate depth.

    When depth = 0, return a brief representation of the related object, containing URL, PK, and object_type.
    When depth > 0, return the data for the appropriate nested serializer, plus a "generic_foreign_key = True" field.

    Args:
        serializer (BaseSerializer): BaseSerializer
        depth (int): Levels of nested serialization
        obj (BaseModel): Object needs to be serialized
        obj_related_field (BaseModel): Related object needs to be serialized
        obj_related_field_name (str): Object's field name that represents the related object.
    """
    if depth == 0:
        url = obj_related_field.get_absolute_url(api=True)
        if serializer.context.get("request"):
            url = serializer.context.get("request").build_absolute_uri(url)

        result = {
            "id": obj_related_field.pk,
            "object_type": obj_related_field._meta.label_lower,
            "url": url,
        }
        return result
    else:
        relation_info = get_relation_info_for_nested_serializers(obj, obj_related_field, obj_related_field_name)
        field_class, field_kwargs = serializer.build_nested_field(obj_related_field_name, relation_info, depth)
        data = field_class(
            obj_related_field, context={"request": serializer.context.get("request")}, **field_kwargs
        ).data
        data["generic_foreign_key"] = True
        return data
