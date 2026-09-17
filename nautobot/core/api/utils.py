from collections import namedtuple
import logging
import platform
import sys

from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.urls import NoReverseMatch, reverse
from rest_framework import serializers, status
from rest_framework.utils import formatting
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.model_meta import _get_to_field, RelationInfo

from nautobot.core.api import exceptions
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.permissions import permission_is_exempt, qs_filter_from_constraints

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

    If the requesting user does not have permission to view the related object at depth > 0, its representation is
    downgraded to the brief form plus a "display" field, exposing the same information a brief representation would
    at depth 0 while additionally surfacing the human-friendly display value (for parity with the UI) rather than
    hiding the object entirely.

    Args:
        serializer (BaseSerializer): BaseSerializer
        depth (int): Levels of nested serialization
        obj (BaseModel): Object needs to be serialized
        obj_related_field (BaseModel): Related object needs to be serialized
        obj_related_field_name (str): Object's field name that represents the related object.
    """
    request = serializer.context.get("request")
    if depth == 0:
        # Brief representation for a depth-0 (leaf) object; no "display" field, to avoid adding cost at depth 0.
        return get_brief_representation(obj_related_field, request)
    if not user_can_view_object(request, obj_related_field):
        # Object would be fully serialized due to depth, but is downgraded due to permissions. Include "display"
        # (no "generic_foreign_key" flag) so that the human-friendly value is still exposed, matching the UI.
        return get_brief_representation(obj_related_field, request, include_display=True)
    relation_info = get_relation_info_for_nested_serializers(obj, obj_related_field, obj_related_field_name)
    field_class, field_kwargs = serializer.build_nested_field(obj_related_field_name, relation_info, depth)
    data = field_class(obj_related_field, context={"request": request}, **field_kwargs).data
    data["generic_foreign_key"] = True
    return data


def get_brief_representation(instance, request=None, *, include_display=False):
    """
    Return the "brief" representation of a related object: `{id, object_type, url}`.

    This is used both for depth-0 serialization of GenericForeignKey fields and to downgrade related objects
    that the requesting user is not permitted to view at depth > 0.

    Args:
        instance (Model): The related object to represent.
        request (Request): The active request, if any, used to build an absolute URL.
        include_display (bool): If True, additionally include the object's human-friendly `display` value. This
            should be set only when downgrading an object that would otherwise have been fully serialized due to
            `?depth`, NOT for objects that are only ever exposed in brief form at a depth boundary (so that
            depth-0 serialization is not made any more expensive).
    """
    model = type(instance)
    url = None
    try:
        url = instance.get_absolute_url(api=True)
    except (AttributeError, NoReverseMatch):
        # Non-Nautobot models (e.g. auth.Group) don't implement get_absolute_url(api=True); fall back to reverse().
        try:
            url = reverse(get_route_for_model(model, "detail", api=True), kwargs={"pk": instance.pk})
        except NoReverseMatch:
            url = None
    if url is not None and request is not None:
        url = request.build_absolute_uri(url)
    result = {
        "id": instance.pk,
        "object_type": model._meta.label_lower,
        "url": url,
    }
    if include_display:
        result["display"] = getattr(instance, "display", str(instance))
    return result


def user_can_view_object(request, instance):
    """
    Return whether the requesting user is permitted to view the given related object.

    Used to decide whether a related object serialized at depth > 0 should be rendered in full or downgraded to
    its brief `{id, object_type, url}` representation.

    This mirrors the semantics of `RestrictedQuerySet.restrict(user, "view")` but avoids issuing a database
    query in the common cases (superuser, exempt permission, unauthenticated, no permission, or model-level
    access). A per-object database check is performed only for users whose view permission is object-constrained,
    and the result is memoized on the request to avoid N+1 queries when the same related object appears multiple
    times in a single response (as is common at depth, especially with `?exclude_m2m=false`).
    """
    # No request (e.g. internal/non-HTTP serialization): don't downgrade.
    if request is None:
        return True
    user = getattr(request, "user", None)
    if user is None:
        return True

    model = type(instance)
    permission_required = f"{model._meta.app_label}.view_{model._meta.model_name}"

    # Superusers and exempt permissions always grant access (no query).
    if user.is_active and user.is_superuser:
        return True
    if permission_is_exempt(permission_required):
        return True
    # Anonymous or inactive users have no object permissions.
    if not user.is_authenticated:
        return False
    # User has not been granted the view permission for this model at all (no query; cached on the user).
    if permission_required not in user.get_all_permissions():
        return False
    # Model-level access (an unconstrained grant, or a non-object permission) => visible without a query.
    constraints = user._object_perm_cache.get(permission_required)
    if not constraints or any(not constraint for constraint in constraints):
        return True

    # Object-level constraints: perform a memoized per-object database check.
    cache = getattr(request, "_depth_view_perm_cache", None)
    if cache is None:
        cache = {}
        request._depth_view_perm_cache = cache
    cache_key = (model._meta.label_lower, instance.pk)
    if cache_key not in cache:
        query_filter = qs_filter_from_constraints(constraints, {"$user": user})
        cache[cache_key] = model._default_manager.filter(query_filter, pk=instance.pk).exists()
    return cache[cache_key]
