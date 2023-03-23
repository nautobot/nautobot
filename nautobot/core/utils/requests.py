import copy
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.utils.functional import SimpleLazyObject
import django_filters

from nautobot.core import constants, exceptions
from nautobot.core.utils.filtering import get_filterset_field


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
            # We have a user but haven't stored its PK yet, so look it up and store it
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
        for k in constants.HTTP_REQUEST_META_SAFE_COPY
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


def convert_querydict_to_factory_formset_acceptable_querydict(request_querydict, filterset_class):
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
    filterset_class_fields = filterset_class().filters.keys()

    query_dict.setdefault("form-INITIAL_FORMS", 0)
    query_dict.setdefault("form-MIN_NUM_FORMS", 0)
    query_dict.setdefault("form-MAX_NUM_FORMS", 100)

    lookup_field_placeholder = "form-%d-lookup_field"
    lookup_type_placeholder = "form-%d-lookup_type"
    lookup_value_placeholder = "form-%d-lookup_value"

    num = 0
    request_querydict = request_querydict.copy()
    request_querydict.pop("q", None)
    for lookup_type, value in request_querydict.items():
        # Discard fields without values
        if value:
            if lookup_type in filterset_class_fields:
                lookup_field = re.sub(r"__\w+", "", lookup_type)
                lookup_value = request_querydict.getlist(lookup_type)

                query_dict.setlistdefault(lookup_field_placeholder % num, [lookup_field])
                query_dict.setlistdefault(lookup_type_placeholder % num, [lookup_type])
                query_dict.setlistdefault(lookup_value_placeholder % num, lookup_value)
                num += 1

    query_dict.setdefault("form-TOTAL_FORMS", max(num, 3))
    return query_dict


def ensure_content_type_and_field_name_in_query_params(query_params):
    """Ensure `query_params` includes `content_type` and `field_name` and `content_type` is a valid ContentType.

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


def is_single_choice_field(filterset_class, field_name):
    # Some filter parameters do not accept multiple values, e.g DateTime, Boolean, Int fields and the q field, etc.
    field = get_filterset_field(filterset_class, field_name)
    return not isinstance(field, django_filters.MultipleChoiceFilter)


def get_filterable_params_from_filter_params(filter_params, non_filter_params, filterset_class):
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
                _is_single_choice_field = is_single_choice_field(filterset_class, field)
            except exceptions.FilterSetFieldNotFound:
                _is_single_choice_field = False

            final_filter_params[field] = (
                filter_params.get(field) if _is_single_choice_field else filter_params.getlist(field)
            )

    return final_filter_params


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
