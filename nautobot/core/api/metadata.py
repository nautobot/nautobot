from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404
import drf_react_template.schema_form_encoder as schema
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from nautobot.core.utils.lookup import get_table_for_model


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
        result = {}
        type_map_obj = self._get_type_map_value(field)
        result["type"] = type_map_obj["type"]
        result["title"] = self._get_title(field, name)

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
            if field.allow_null:
                result["type"] = [result["type"], "null"]
            enum = type_map_obj.get("enum")
            if enum:
                if enum == "choices":
                    choices = field.choices
                    result["enum"] = list(choices.keys())
                    result["enumNames"] = list(choices.values())
                if isinstance(enum, (list, tuple)):
                    if isinstance(enum, (list, tuple)):
                        result["enum"] = [item[0] for item in enum]
                        result["enumNames"] = [item[1] for item in enum]
                    else:
                        result["enum"] = enum
                        result["enumNames"] = list(enum)

            # Process "format"
            format_ = type_map_obj["format"]
            if format_:
                result["format"] = format_

            # Process "readOnly"
            read_only = type_map_obj["readOnly"]
            if read_only:
                result["readOnly"] = read_only

            try:
                result["default"] = field.get_default()
            except drf_fields.SkipField:
                pass

        result = self._set_validation_properties(field, result)

        return result


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
        if not serializer_meta:
            return []
        table = get_table_for_model( serializer_meta.model)
        return list(getattr(table.Meta, "default_columns", [])) if table else []

    def determine_view_options(self, request, serializer):
        """Determine view options that will be used for non-form display metadata."""
        view_options = {}
        list_display = []
        fields = []

        processor = NautobotColumnProcessor(serializer, request.parser_context)
        field_map = dict(processor.fields)
        all_fields = list(field_map)

        # Explicitly order the "big ugly" fields to the bottom.
        processor.order_fields(all_fields)

        list_display_fields = self.get_list_display_fields(serializer)

        # Process the list_display fields first.
        for field_name in list_display_fields:
            try:
                field = field_map[field_name]
            except KeyError:
                continue  # Ignore unknown fields.
            column_data = processor._get_column_properties(field, field_name)
            list_display.append(column_data)
            fields.append(column_data)

        # Process the rest of the fields second.
        for field_name in all_fields:
            # Don't process list display fields twice.
            if field_name in list_display_fields:
                continue
            try:
                field = field_map[field_name]
            except KeyError:
                continue  # Ignore unknown fields.
            column_data = processor._get_column_properties(field, field_name)
            fields.append(column_data)

        view_options["list_display_fields"] = list_display
        view_options["fields"] = fields

        return view_options

    def determine_metadata(self, request, view):
        """This is the metadata that gets returned on an `OPTIONS` request."""
        metadata = super().determine_metadata(request, view)

        # If there's a serializer, do the needful to bind the schema/uiSchema.
        if hasattr(view, "get_serializer"):
            serializer = view.get_serializer()
            # TODO(jathan): Bit of a WIP here. Will likely refactor. There might be cases where we
            # want to explicitly override the UI field ordering, but that's not yet accounted for
            # here. For now the assertion is always put the `list_display_fields` first, and then
            # include the rest in whatever order.
            # See: https://rjsf-team.github.io/react-jsonschema-form/docs/usage/objects#specifying-property-order
            ui_schema = NautobotUiSchemaProcessor(serializer, request.parser_context).get_ui_schema()
            ui_schema["ui:order"] = self.get_list_display_fields(serializer) + ["*"]
            metadata.update(
                {
                    "schema": NautobotSchemaProcessor(serializer, request.parser_context).get_schema(),
                    # "uiSchema": NautobotUiSchemaProcessor(serializer, request.parser_context).get_ui_schema(),
                    "uiSchema": ui_schema,
                }
            )

            metadata["view_options"] = self.determine_view_options(request, serializer)

        return metadata
