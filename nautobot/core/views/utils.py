import datetime
from io import BytesIO
import logging
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import FieldError, ValidationError
from django.db.models import ForeignKey
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django_tables2 import RequestConfig
from prometheus_client import REGISTRY
from prometheus_client.utils import floatToGoString
from rest_framework import exceptions, serializers

from nautobot.core.api.fields import ChoiceField, ContentTypeField, TimeZoneSerializerField
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.models.utils import is_taggable
from nautobot.core.utils import lookup
from nautobot.core.utils.data import is_uuid
from nautobot.core.utils.filtering import get_filter_field_label
from nautobot.core.utils.lookup import (
    get_created_and_last_updated_usernames_for_model,
    get_filterset_for_model,
    get_form_for_model,
    get_view_for_model,
)
from nautobot.core.utils.requests import normalize_querydict
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.models import SavedView
from nautobot.extras.tables import AssociatedContactsTable, DynamicGroupTable, ObjectMetadataTable

logger = logging.getLogger(__name__)

METRICS_CACHE_KEY = "nautobot_app_metrics_cache"
always_generated_metrics = [
    "nautobot_app_metrics_processing_ms"  # Always generate this metric to track the processing time of Nautobot App metrics, improved with caching.
]


def check_filter_for_display(filters, field_name, values):
    """
    Return any additional context data for the template.

    Args:
        filters (dict): The filters of a desired FilterSet
        field_name (str): The name of the filter to get a label for and lookup values
        values (list[str]): List of strings that may be PKs to look up

    Returns:
        (dict): A dict containing:
            - name: (str) Field name
            - display: (str) Resolved field name, whether that's a field label or fallback to inputted `field_name` if label unavailable
            - values: (list) List of dictionaries with the same `name` and `display` keys
    """
    values = values if isinstance(values, (list, tuple)) else [values]

    resolved_filter = {
        "name": field_name,
        "display": field_name,
        "values": [{"name": value, "display": value} for value in values],
    }

    if field_name not in filters.keys():
        return resolved_filter

    filter_field = filters[field_name]

    resolved_filter["display"] = get_filter_field_label(filter_field)

    if len(values) == 0 or not hasattr(filter_field, "queryset") or not is_uuid(values[0]):
        return resolved_filter
    else:
        try:
            new_values = []
            for value in filter_field.queryset.filter(pk__in=values):
                new_values.append({"name": str(value.pk), "display": getattr(value, "display", str(value))})
            resolved_filter["values"] = new_values
        except (FieldError, AttributeError):
            pass

    return resolved_filter


# 2.2 TODO: remove this method as it's no longer used in core.
def csv_format(data):
    """
    Convert the given list of data to a CSV row string.

    Encapsulate any data which contains a comma within double quotes.

    Obsolete, as CSV rendering in Nautobot core is now handled by nautobot.core.api.renderers.NautobotCSVRenderer.
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


def get_obj_from_context(context, key=None):
    """From the given context, return the `object` that is in the context.

    If a key is specified, return the value for that key.
    Otherwise return the value for either of the keys `"obj"` or `"object"` as default behavior.
    """
    if key is not None:
        return context.get(key)
    return context.get("obj") or context.get("object")


def get_csv_form_fields_from_serializer_class(serializer_class):
    """From the given serializer class, build a list of field dicts suitable for rendering in the CSV import form."""
    serializer = serializer_class(context={"request": None, "depth": 0})
    fields = []
    # Note lots of "noqa: S308" in this function. That's `suspicious-mark-safe-usage`, but in all of the below cases
    # we control the input string and it's known to be safe, so mark_safe() is being used correctly here.
    for field_name, field in serializer.fields.items():
        if field.read_only:
            continue
        if field_name == "custom_fields":
            from nautobot.extras.choices import CustomFieldTypeChoices
            from nautobot.extras.models import CustomField

            cfs = CustomField.objects.get_for_model(serializer_class.Meta.model, get_queryset=False)
            for cf in cfs:
                cf_form_field = cf.to_form_field(set_initial=False)
                field_info = {
                    "name": cf.add_prefix_to_cf_key(),
                    "required": cf_form_field.required,
                    "foreign_key": False,
                    "label": cf_form_field.label,
                    "help_text": cf_form_field.help_text,
                }
                if cf.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
                    field_info["format"] = mark_safe("<code>true</code> or <code>false</code>")
                elif cf.type == CustomFieldTypeChoices.TYPE_DATE:
                    field_info["format"] = mark_safe("<code>YYYY-MM-DD</code>")
                elif cf.type == CustomFieldTypeChoices.TYPE_SELECT:
                    field_info["choices"] = {value: value for value in cf.choices}
                elif cf.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
                    field_info["format"] = mark_safe('<code>"value,value"</code>')
                    field_info["choices"] = {value: value for value in cf.choices}
                fields.append(field_info)
            continue

        field_info = {
            "name": field_name,
            "required": field.required,
            "foreign_key": False,
            "label": field.label,
            "help_text": field.help_text,
        }
        if isinstance(field, serializers.BooleanField):
            field_info["format"] = mark_safe("<code>true</code> or <code>false</code>")
        elif isinstance(field, serializers.DateField):
            field_info["format"] = mark_safe("<code>YYYY-MM-DD</code>")
        elif isinstance(field, TimeZoneSerializerField):
            field_info["format"] = mark_safe(
                '<a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">available options</a>'
            )
        elif isinstance(field, serializers.ManyRelatedField):
            if field.field_name == "tags":
                field_info["format"] = mark_safe('<code>"name,name"</code> or <code>"UUID,UUID"</code>')
            elif isinstance(field.child_relation, ContentTypeField):
                field_info["format"] = mark_safe('<code>"app_label.model,app_label.model"</code>')
            else:
                field_info["foreign_key"] = field.child_relation.queryset.model._meta.label_lower
                field_info["format"] = mark_safe('<code>"UUID,UUID"</code> or combination of fields')
        elif isinstance(field, serializers.RelatedField):
            if isinstance(field, ContentTypeField):
                field_info["format"] = mark_safe("<code>app_label.model</code>")
            else:
                field_info["foreign_key"] = field.queryset.model._meta.label_lower
                field_info["format"] = mark_safe("<code>UUID</code> or combination of fields")
        elif isinstance(field, (serializers.ListField, serializers.MultipleChoiceField)):
            field_info["format"] = mark_safe('<code>"value,value"</code>')
        elif isinstance(field, (serializers.DictField, serializers.JSONField)):
            pass  # Not trivial to specify a format as it could be a JSON dict or a comma-separated string

        if isinstance(field, ChoiceField):
            field_info["choices"] = field.choices

        fields.append(field_info)

    # Move all required fields to the start of the list
    # TODO this ordering should be defined by the serializer instead...
    fields = sorted(fields, key=lambda info: 1 if info["required"] else 2)
    return fields


def import_csv_helper(*, request, form, serializer_class):
    field_name = "csv_file" if request.FILES else "csv_data"
    csvtext = form.cleaned_data[field_name]
    try:
        data = NautobotCSVParser().parse(
            stream=BytesIO(csvtext.encode("utf-8")),
            parser_context={"request": request, "serializer_class": serializer_class},
        )
        new_objs = []
        validation_failed = False
        for row, entry in enumerate(data, start=1):
            serializer = serializer_class(data=entry, context={"request": request})
            if serializer.is_valid():
                new_objs.append(serializer.save())
            else:
                validation_failed = True
                for field, err in serializer.errors.items():
                    form.add_error(field_name, f"Row {row}: {field}: {err[0]}")
    except exceptions.ParseError as exc:
        validation_failed = True
        form.add_error(None, str(exc))

    if validation_failed:
        raise ValidationError("")

    return new_objs


def handle_protectederror(obj_list, request, e):
    """
    Generate a user-friendly error message in response to a ProtectedError exception.
    """
    protected_objects = list(e.protected_objects)
    protected_count = len(protected_objects) if len(protected_objects) <= 50 else "More than 50"
    err_message = format_html(
        str(e.args[0]) if e.args else "Unable to delete <strong>{}</strong>. {} dependent objects were found: ",
        ", ".join(str(obj) for obj in obj_list),
        protected_count,
    )

    # Format objects based on whether they have a detail view/absolute url
    objects_with_absolute_url = []
    objects_without_absolute_url = []
    # Append dependent objects to error message
    for dependent in protected_objects[:50]:
        try:
            dependent.get_absolute_url()
            objects_with_absolute_url.append(dependent)
        except AttributeError:
            objects_without_absolute_url.append(dependent)

    err_message += format_html_join(
        ", ",
        '<a href="{}">{}</a>',
        ((dependent.get_absolute_url(), dependent) for dependent in objects_with_absolute_url),
    )
    if objects_with_absolute_url and objects_without_absolute_url:
        err_message += format_html(", ")
    err_message += format_html_join(
        ", ",
        "<span>{}</span>",
        ((dependent,) for dependent in objects_without_absolute_url),
    )

    messages.error(request, err_message)


def prepare_cloned_fields(instance):
    """
    Compile an object's `clone_fields` list into a string of URL query parameters. Tags are automatically cloned where
    applicable.
    """
    form_class = get_form_for_model(instance)
    form = form_class(instance=instance) if form_class is not None else None
    params = []
    for field_name in getattr(instance, "clone_fields", []):
        field = instance._meta.get_field(field_name)
        field_value = field.value_from_object(instance)

        # For foreign-key fields, if the ModelForm's field has a defined `to_field_name`,
        # use that field from the related object instead of its PK.
        # Example: Location.parent, LocationForm().fields["parent"].to_field_name = "name", so use name rather than PK.
        if isinstance(field, ForeignKey):
            related_object = getattr(instance, field_name)
            if (
                related_object is not None
                and form is not None
                and field_name in form.fields
                and hasattr(form.fields[field_name], "to_field_name")
                and form.fields[field_name].to_field_name is not None
            ):
                field_value = getattr(related_object, form.fields[field_name].to_field_name)

        # Swap out False with URL-friendly value
        if field_value is False:
            field_value = ""

        # Handle M2M fields or lists
        if hasattr(field_value, "all") and callable(field_value.all):
            # This is a manager for a M2M relationship
            for related_obj in field_value.all():
                item_value = getattr(related_obj, "pk", str(related_obj))  # pk or str()
                params.append((field_name, item_value))
        # This is likely a list from another type of field
        elif isinstance(field_value, list):
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

    # Encode the parameters into a URL query string
    param_string = urllib.parse.urlencode(params)

    return param_string


def view_changes_not_saved(request, view, current_saved_view):
    """
    Compare request.GET's query dict with the configuration stored on the current saved view
    If there is any configuration different, return True
    If every configuration is the same, return False
    """
    if current_saved_view is None:
        return True
    query_dict = request.GET.dict()

    if "table_changes_pending" in query_dict or "all_filters_removed" in query_dict:
        return True
    per_page = int(query_dict.get("per_page", 0))
    if per_page and per_page != current_saved_view.config.get("pagination_count"):
        return True
    sort = request.GET.getlist("sort", [])
    if sort and sort != current_saved_view.config.get("sort_order", []):
        return True
    query_dict_keys = sorted(list(query_dict.keys()))
    for param in view.non_filter_params:
        if param in query_dict_keys:
            query_dict_keys.remove(param)
    filter_params = current_saved_view.config.get("filter_params", {})

    if query_dict_keys:
        if set(query_dict_keys) != set(filter_params.keys()):
            return True
        for key, value in filter_params.items():
            if set(value) != set(request.GET.getlist(key)):
                return True
    return False


def common_detail_view_context(request, instance):
    """Additional template context for object detail views, shared by both ObjectView and NautobotHTMLRenderer."""
    context = {}

    created_by, last_updated_by = get_created_and_last_updated_usernames_for_model(instance)
    context["created_by"] = created_by
    context["last_updated_by"] = last_updated_by
    context["detail"] = True

    if getattr(instance, "is_contact_associable_model", False):
        paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        associations = instance.associated_contacts.restrict(request.user, "view").order_by("role__name")
        associations_table = AssociatedContactsTable(associations, orderable=False)
        RequestConfig(request, paginate).configure(associations_table)
        associations_table.columns.show("pk")
        context["associated_contacts_table"] = associations_table
    else:
        context["associated_contacts_table"] = None

    if getattr(instance, "is_dynamic_group_associable_model", False):
        paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        dynamic_groups = instance.dynamic_groups.restrict(request.user, "view")
        dynamic_groups_table = DynamicGroupTable(dynamic_groups, orderable=False)
        dynamic_groups_table.columns.hide("content_type")
        RequestConfig(request, paginate).configure(dynamic_groups_table)
        # dynamic_groups_table.columns.show("pk")  # we don't have any supported bulk ops here presently
        context["associated_dynamic_groups_table"] = dynamic_groups_table
    else:
        context["associated_dynamic_groups_table"] = None

    if getattr(instance, "is_metadata_associable_model", False):
        paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        object_metadata = instance.associated_object_metadata.restrict(request.user, "view").order_by(
            "metadata_type", "scoped_fields"
        )
        object_metadata_table = ObjectMetadataTable(object_metadata, orderable=False)
        object_metadata_table.columns.hide("assigned_object")
        RequestConfig(request, paginate).configure(object_metadata_table)
        context["associated_object_metadata_table"] = object_metadata_table
    else:
        context["associated_object_metadata_table"] = None

    return context


def get_saved_views_for_user(user, list_url):
    # We are not using .restrict(request.user, "view") here
    # User should be able to see any saved view that he has the list view access to.
    saved_views = SavedView.objects.filter(view=list_url).order_by("name").only("pk", "name")
    if user.has_perms(["extras.view_savedview"]):
        return saved_views

    shared_saved_views = saved_views.filter(is_shared=True)
    if user.is_authenticated:
        user_owned_saved_views = SavedView.objects.filter(view=list_url, owner=user).order_by("name").only("pk", "name")
        return shared_saved_views | user_owned_saved_views

    return shared_saved_views


def is_metrics_experimental_caching_enabled():
    """Return True if METRICS_EXPERIMENTAL_CACHING_DURATION is set to a positive integer."""
    return settings.METRICS_EXPERIMENTAL_CACHING_DURATION > 0


def generate_latest_with_cache(registry=REGISTRY):
    """A vendored version of prometheus_client.generate_latest that caches Nautobot App metrics."""

    def sample_line(line):
        if line.labels:
            labelstr = "{{{0}}}".format(
                ",".join(
                    [
                        '{}="{}"'.format(k, v.replace("\\", r"\\").replace("\n", r"\n").replace('"', r"\""))
                        for k, v in sorted(line.labels.items())
                    ]
                )
            )
        else:
            labelstr = ""
        timestamp = ""
        if line.timestamp is not None:
            # Convert to milliseconds.
            timestamp = f" {int(float(line.timestamp) * 1000):d}"
        return f"{line.name}{labelstr} {floatToGoString(line.value)}{timestamp}\n"

    cached_lines = []
    output = []
    # NOTE: In the original prometheus_client code the lines are written to output directly,
    # here we are going to cache some lines so we need to build each metric's output separately.
    # So instead of `output.append(line)` we do
    # `this_metric_output.append(line)` and then `output.extend(this_metric_output)`
    for metric in registry.collect():
        this_metric_output = []
        try:
            mname = metric.name
            mtype = metric.type
            # Munging from OpenMetrics into Prometheus format.
            if mtype == "counter":
                mname = mname + "_total"
            elif mtype == "info":
                mname = mname + "_info"
                mtype = "gauge"
            elif mtype == "stateset":
                mtype = "gauge"
            elif mtype == "gaugehistogram":
                # A gauge histogram is really a gauge,
                # but this captures the structure better.
                mtype = "histogram"
            elif mtype == "unknown":
                mtype = "untyped"

            this_metric_output.append(
                "# HELP {} {}\n".format(mname, metric.documentation.replace("\\", r"\\").replace("\n", r"\n"))
            )
            this_metric_output.append(f"# TYPE {mname} {mtype}\n")

            om_samples = {}
            for s in metric.samples:
                for suffix in ["_created", "_gsum", "_gcount"]:
                    if s.name == metric.name + suffix:
                        # OpenMetrics specific sample, put in a gauge at the end.
                        om_samples.setdefault(suffix, []).append(sample_line(s))
                        break
                else:
                    this_metric_output.append(sample_line(s))
        except Exception as exception:
            exception.args = (exception.args or ("",)) + (metric,)
            raise

        for suffix, lines in sorted(om_samples.items()):
            this_metric_output.append(
                "# HELP {}{} {}\n".format(
                    metric.name, suffix, metric.documentation.replace("\\", r"\\").replace("\n", r"\n")
                )
            )
            this_metric_output.append(f"# TYPE {metric.name}{suffix} gauge\n")
            this_metric_output.extend(lines)

        # BEGIN Nautobot-specific logic
        # If the metric name starts with nautobot_, we cache the lines
        if metric.name.startswith("nautobot_") and metric.name not in always_generated_metrics:
            cached_lines.extend(this_metric_output)
        # END Nautobot-specific logic

        # Always add the metric output to the final output
        output.extend(this_metric_output)

    # BEGIN Nautobot-specific logic
    # Add in any previously cached metrics.
    # Note that this is mutually-exclusive with the above block, that is to say,
    # either cached_lines will be populated OR collector.local_cache will be populated,
    # never both at the same time.
    for collector in registry._collector_to_names:
        # This is to avoid a race condition where between the time to collect the metrics and
        # the time to generate the output, the cache is expired and we miss some metrics.
        if hasattr(collector, "local_cache") and collector.local_cache:
            output.extend(collector.local_cache)
            del collector.local_cache  # avoid re-using stale data on next call

    # If we have any cached lines, and the cache is empty or expired, update the cache.
    if cached_lines and not cache.get(METRICS_CACHE_KEY):
        cache.set(METRICS_CACHE_KEY, cached_lines, timeout=settings.METRICS_EXPERIMENTAL_CACHING_DURATION)
    # END Nautobot-specific logic

    return "".join(output).encode("utf-8")


def get_bulk_queryset_from_view(
    user, content_type, filter_query_params, pk_list, saved_view_id, action, delete_all=None, edit_all=None, log=None
):
    """
    Return a queryset for bulk operations based on the provided parameters.

    Args:
        user: The user performing the bulk operation.
        model: The model class on which the bulk operation is being performed.
        delete_all: Boolean indicating whether the operation applies to pk_list or not.
        edit_all: Boolean indicating whether the operation applies to pk_list or not.
        filter_query_params: A dictionary of filter parameters to apply to the queryset as produced by convert_querydict_to_dict(request.GET).
        pk_list: A list of primary keys to include, when not using a filter.
        saved_view_id: (Optional) UUID of a saved view to apply additional filters from.

    Returns:
        A Django queryset representing the objects to be affected by the bulk operation.

    Notes:
        Start
        ├── !is_all and pk_list: Return queryset filtered by pk_list
        ├── !is_all and !pk_list: Return empty queryset
        ├── is_all and !saved_view_id and !filter_query_params: Return all objects
        ├── is_all and filter_query_params: Return queryset filtered by filter_query_params
        ├── is_all and saved_view_id: Return queryset filtered by saved_view_filter_params
        ├── is_all and not saved_view_id: Return queryset filtered by saved_view_filter_params
        └── else: raise RuntimeError
    """
    model = content_type.model_class()
    if not log:
        log = logger

    action_valid = (action == "delete" and delete_all is not None) or (action == "change" and edit_all is not None)
    if not action_valid:
        raise RuntimeError(
            f"Invalid parameters *_all param for action {action}, got: delete_all={delete_all}, edit_all={edit_all}"
        )

    view_name = None
    is_all = None
    # Based on action_valid one of these must be True
    if action == "delete":
        view_name = "BulkDelete"
        is_all = delete_all
    elif action == "change":
        view_name = "BulkEdit"
        is_all = edit_all

    # The view_class is determined from model on purpose, as view_class the view as a param, will not work
    # with a job. It is better to be consistent with each with sending the same params that will
    # always be available from to the confirmation page and to the job.
    view_class = get_view_for_model(model, view_type=view_name)

    if not view_class:
        raise RuntimeError(f"No view found for model {model} to determine base queryset.")

    queryset = view_class.queryset.restrict(user, action)

    # The filterset_class is determined from model on purpose versus getting it from the view itself. This is
    # because the filterset_class on the view as a param, will not work with a job. It is better to be consistent
    # with each with sending the same params that will always be available from to the confirmation page and to the job.
    filterset_class = get_filterset_for_model(model)

    if not filterset_class:
        log.debug(f"No filterset_class found for model {model}, returning all objects")
        return queryset

    filterset_class = lookup.get_filterset_for_model(model)
    if filterset_class:
        filter_query_params = normalize_querydict(filter_query_params, filterset=filterset_class())
        log.debug(f"Normalized filter_query_params: {filter_query_params}")
    else:
        filter_query_params = {}

    # The form actually sends the pks and the "all" parameter, so seeing pk_list by itself is not
    # sufficient to determine if we are filtering by pk_list or by all. We need to see is_all=False.
    if not is_all and pk_list:
        log.debug("Filtering by PK list")
        return queryset.filter(pk__in=pk_list)

    # Should this ever happen?
    if not is_all and not pk_list:
        log.debug("Filtering by None, as no PKs provided for bulk operation, returning empty queryset")
        return queryset.none()

    # The query params when you manually delete filters from the UI include on the saved view filter
    # set the flag all_filters_removed to true. If that is the case, we ignore the saved view below, by setting it
    # to None here
    if filter_query_params.get("all_filters_removed"):
        log.debug("The `all_filters_removed` flag is set, ignoring saved view")
        saved_view_id = None
        filter_query_params.pop("all_filters_removed")

    new_filter_query_params = {}

    filterset = filterset_class()
    for key, value in filter_query_params.items():
        if filterset.filters.get(key) is not None:
            new_filter_query_params[key] = value
        else:
            log.debug(f"Query parameter `{key}` not found in `{filterset_class}`, discarding it")
    filter_query_params = new_filter_query_params

    # short circuit if no filtering is needed
    if is_all and not saved_view_id and not filter_query_params:
        log.debug("No filters or saved view specified, returning all objects")
        return queryset

    # This covers if there is a filter and a saved view, as when you have both,
    # the saved view filters show up in the query params or the url.
    if is_all and filter_query_params:
        log.debug(f"Filtering by parameters: {filter_query_params}")
        inner_queryset = filterset_class(filter_query_params, queryset).qs.values("pk")
        # We take this approach because filterset.qs has already applied .distinct(),
        # and performing a .delete directly on a queryset with .distinct applied is not allowed.
        return queryset.filter(pk__in=inner_queryset)

    saved_view_filter_params = {}
    if saved_view_id:
        try:
            saved_view_obj = SavedView.objects.get(id=saved_view_id)
        except SavedView.DoesNotExist:
            return queryset.none()
        saved_view_filter_params = saved_view_obj.config.get("filter_params", {})

    # This covers the case where there is a saved view but no additional filter parameters.
    if is_all and saved_view_filter_params:
        log.debug(f"Filtering by saved view parameters: {saved_view_filter_params}")
        inner_queryset = filterset_class(saved_view_filter_params, queryset).qs.values("pk")
        # We take this approach because filterset.qs has already applied .distinct(),
        # and performing a .delete directly on a queryset with .distinct applied is not allowed.
        return queryset.filter(pk__in=inner_queryset)

    # short circuit if no filtering is applied with a saved view
    if is_all and not saved_view_filter_params:
        log.debug("Saved view with no filters specified, returning all objects")
        return queryset

    log.debug("No valid operation found to generate bulk queryset.")
    raise RuntimeError("No valid operation found to generate bulk queryset.")
