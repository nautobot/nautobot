import contextlib
from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
import django_filters
import drf_react_template.schema_form_encoder as schema
from rest_framework import exceptions, fields as drf_fields, serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from nautobot.core.utils.filtering import build_lookup_label, get_filter_field_label
from nautobot.core.utils.lookup import get_route_for_model

# FIXME(jathan): I hate this pattern that these fields are hard-coded here. But for the moment, this
# works reliably.
BOTTOM_FIELDS = ["computed_fields", "custom_fields", "relationships"]


class NautobotProcessingMixin(schema.ProcessingMixin):
    """Processing mixin to account for custom field types and behaviors for Nautobot."""

    def _get_type_map_value(self, field: schema.SerializerType):
        """Overload default to add "required" as a default mapping."""
        # This adds "required" as a default type mapping compared to drf_react_template core.
        result = {
            "type": field.style.get("schema:type"),
            "enum": field.style.get("schema:enum"),
            "format": field.style.get("schema:format"),
            "widget": field.style.get("ui:widget"),
            "required": field.style.get("schema:required"),
            "readOnly": field.style.get("schema:readOnly"),
        }
        result_default = self.TYPE_MAP.get(type(field).__name__, {})
        for k in result_default:
            if result[k] is None:
                result[k] = result_default[k]
        return result

    def order_fields(self, fields):
        """Explicitly order the "big ugly" fields to the bottom."""
        # FIXME(jathan): Correct the behavior introduced in #3500 by switching to `__all__` to
        # assert these get added at the end.
        for field_name in BOTTOM_FIELDS:
            if field_name in fields:
                fields.remove(field_name)
                fields.append(field_name)
        return fields


class NautobotSchemaProcessor(NautobotProcessingMixin, schema.SchemaProcessor):
    """SchemaProcessor to account for custom field types and behaviors for Nautobot."""

    def _get_field_properties(self, field: schema.SerializerType, name: str) -> Dict[str, Any]:
        """
        This method is used to generate the proper schema based on serializer field mappings or
        per-field attribute markup.

        This has been overloaded with an `elif` to account for `ManyRelatedField`.
        """
        type_map_obj = self._get_type_map_value(field)
        result = {
            "type": type_map_obj["type"] or "string",
            "title": self._get_title(field, name),
        }

        if isinstance(field, drf_serializers.ListField):
            if field.allow_empty:
                result["required"] = not getattr(field, "allow_empty", True)
            result["items"] = self._get_field_properties(field.child, "")
            result["uniqueItems"] = True
        elif isinstance(field, drf_serializers.ManyRelatedField):
            if field.allow_empty:
                result["required"] = type_map_obj.get("required", [])
            result["items"] = self._get_field_properties(field.child_relation, "")
            result["uniqueItems"] = True
        else:
            if isinstance(field, drf_serializers.RelatedField):
                result["uniqueItems"] = True
                if hasattr(field, "queryset") and hasattr(field.queryset, "model"):
                    # We construct the correct list view url here so we can just append the object id to the end of the url in our frontend.
                    # e.g. /dcim/locations/
                    try:
                        model_url = reverse(get_route_for_model(model=field.queryset.model, action="list"))
                    except NoReverseMatch:
                        model_url = None
                    model_options = field.queryset.model._meta
                    result["required"] = field.required
                    # Custom Keyword: modelName, modelNamePlural and appLabel
                    # modelName represents the model name of the uuid model
                    # modelUrl represents the UI URL to list instances of this model
                    # and appLabel represents the app_name of the model
                    result["modelName"] = model_options.model_name
                    result["appLabel"] = model_options.app_label
                    result["modelUrl"] = model_url
            if field.allow_null:
                result["type"] = [result["type"], "null"]
            if enum := type_map_obj.get("enum"):
                if enum == "choices":
                    choices = field.choices
                    result["enum"] = list(choices.keys())
                    result["enumNames"] = list(choices.values())
                if isinstance(enum, (list, tuple)):
                    result["enum"] = [item[0] for item in enum]
                    result["enumNames"] = [item[1] for item in enum]
            if format_ := type_map_obj["format"]:
                result["format"] = format_

            if read_only := field.read_only:
                result["readOnly"] = read_only

            with contextlib.suppress(drf_fields.SkipField):
                result["default"] = field.get_default()

        result = self._set_validation_properties(field, result)

        return result

    @staticmethod
    def _filter_fields(all_fields):
        """
        Override super._filter_fields to return all fields, including read-only fields,
        as read-only fields have to be displayed in Detail View.
        """
        return tuple((name, field) for name, field in all_fields)


class NautobotUiSchemaProcessor(NautobotProcessingMixin, schema.UiSchemaProcessor):
    """UiSchemaProcessor to account for custom field types and behaviors for Nautobot."""

    def _field_order(self) -> List[str]:
        """
        Overload the base which just returns `Meta.fields` and doesn't play nicely with "__all__".

        This instead calls `get_fields()` and returns the keys.
        """
        if self._is_list_serializer(self.serializer):
            fields = self.serializer.child.get_fields()
        else:
            fields = self.serializer.get_fields()

        field_names = self.order_fields(list(fields))

        return field_names

    def _get_ui_field_properties(self, field: schema.SerializerType, name: str) -> Dict[str, Any]:
        """
        We had to overload this here to make it so that array types with children validate properly
        and to also use `NautobotUiSchemaProcessor` over the default.
        """
        data_index = self._generate_data_index(name)
        result = {}
        is_list = False
        if self._is_field_serializer(field):
            return NautobotUiSchemaProcessor(field, self.renderer_context, prefix=data_index).get_ui_schema()
        elif isinstance(field, drf_serializers.ListField):
            is_list = True
            child = field.child
            is_int = isinstance(child, drf_serializers.IntegerField)
            widget = self._get_type_map_value(field=child).get("widget")
            if not widget and isinstance(child, drf_serializers.ChoiceField):
                widget = "checkbox"
        else:
            widget = self._get_type_map_value(field=field).get("widget")
        help_text = field.help_text
        if widget:
            if is_list and is_int:
                if "items" not in result:
                    result["items"] = {}
                result["items"]["ui:widget"] = widget
            else:
                result["ui:widget"] = widget
        if help_text:
            result["ui:help"] = help_text
        result.update(self._get_style_dict(field))
        result = self._set_validation_properties(field, result)
        return result


class NautobotColumnProcessor(NautobotProcessingMixin, schema.ColumnProcessor):
    """ColumnProcessor to account for custom field types and behaviors for Nautobot."""


class NautobotMetadata(SimpleMetadata):
    """
    Metadata class that emits JSON schema. It contains `schema` and `uiSchema` keys where:

    - schema: The object JSON schema
    - uiSchema: The object UI schema which describes the form layout in the UI
    """

    def determine_actions(self, request, view):
        """Generate the actions and return the names of the allowed methods."""
        actions = []
        for method in {"PUT", "POST"} & set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, "check_permissions"):
                    view.check_permissions(view.request)
                # Test object permissions (if viewing a specific object)
                if method == "PUT" and view.lookup_url_kwarg and hasattr(view, "get_object"):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                actions.append(method)
            finally:
                view.request = request
        return actions

    def get_list_display_fields(self, serializer):
        """Try to get the list display fields or default to an empty list."""
        serializer_meta = getattr(serializer, "Meta", None)
        return list(getattr(serializer_meta, "list_display_fields", []))

    def determine_metadata(self, request, view):
        """This is the metadata that gets returned on an `OPTIONS` request."""
        metadata = super().determine_metadata(request, view)

        # Include the object type label for this model.
        object_type = view.queryset.model._meta.label_lower if getattr(view, "queryset", None) else "unknown"
        metadata["object_type"] = object_type

        # If there's a serializer, do the needful to bind the schema/uiSchema.
        if hasattr(view, "get_serializer"):
            serializer = view.get_serializer()
            # TODO(jathan): Bit of a WIP here. Will likely refactor. There might be cases where we
            # want to explicitly override the UI field ordering, but that's not yet accounted for
            # here. For now the assertion is always put the `list_display_fields` first, and then
            # include the rest in whatever order.
            # See: https://rjsf-team.github.io/react-jsonschema-form/docs/usage/objects#specifying-property-order
            ui_schema = NautobotUiSchemaProcessor(serializer, request.parser_context).get_ui_schema()
            ui_schema["ui:order"] = [*self.get_list_display_fields(serializer), "*"]
            metadata.update(
                {
                    "schema": NautobotSchemaProcessor(serializer, request.parser_context).get_schema(),
                    "uiSchema": ui_schema,
                }
            )

            metadata["filters"] = self.get_filter_info(view)

            if hasattr(serializer, "determine_view_options"):
                metadata["view_options"] = serializer.determine_view_options(request)

        return metadata

    def get_filter_info(self, view):
        """Enumerate filterset information for the view. Returns a dictionary with the following format:

        {
            "filter_name": {
                "label": "Filter Label",
                "lookup_types": [
                    {"value": "filter_name__n", "label": "not exact (n)"},
                    {"value": "filter_name__re", "label": "matches regex (re)"},
                    ...
                ]
            }
        }

        """

        if not getattr(view, "filterset_class", None):
            return {}
        filterset = view.filterset_class
        filters = {}
        for filter_name, filter_instance in sorted(
            filterset.base_filters.items(),
            key=lambda x: get_filter_field_label(x[1]),
        ):
            filter_key = filter_name.rsplit("__", 1)[0]
            label = get_filter_field_label(filter_instance)
            lookup_label = self._filter_lookup_label(filter_name, filter_instance)
            filters.setdefault(filter_key, {"label": label})
            filters[filter_key].setdefault("lookup_types", []).append({"value": filter_name, "label": lookup_label})
        return filters

    # TODO: move this into `build_lookup_label` when the legacy UI is removed
    def _filter_lookup_label(self, filter_name, filter_instance):
        """Fix confusing lookup labels for boolean filters."""
        if isinstance(filter_instance, django_filters.BooleanFilter):
            return "exact"
        return build_lookup_label(filter_name, filter_instance.lookup_expr)
