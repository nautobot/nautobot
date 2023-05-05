from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404
import drf_react_template.schema_form_encoder as schema
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from nautobot.core.api.serializers import NautobotPrimaryKeyRelatedField


class NautobotProcessingMixin(schema.ProcessingMixin):
    """Processing mixin  to account for custom field types and behaviors for Nautobot."""

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


class NautobotSchemaProcessor(NautobotProcessingMixin, schema.SchemaProcessor):
    """
    SchemaProcessor to account for custom field types and behaviors for Nautobot.
    """

    def _get_all_field_properties(self):
        """Override to enforce serializer schema/field order if provided"""
        field_properties = super()._get_all_field_properties()
        field_order = getattr(self.serializer.Meta, "field_order", None)
        if not field_order:
            return field_properties

        # TODO:
        #  1: Fix CustomFields Field
        #  2: Decide on wherever to discard fields not defined in the field_order, 
        #       or just add the rest fields after field_order fields
        
        grouping = {}
        
        for group_name, fields in field_order.items():
            fields_data = {name: field_properties.get(name) for name in fields}
            # Some fields on the field_order might not be on the serializer fields; Skip those fields
            if any(fields_data.values()):
                grouping[group_name] = {
                     "type": "object",
                      "properties": fields_data
                }
        return grouping

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

        if isinstance(field, NautobotPrimaryKeyRelatedField):
            model = field.queryset.model
            result["additionalProps"] = {
                "model_name": model._meta.verbose_name_plural.replace(" ", "-"),
                "app_label": model._meta.app_label,
            }
        elif isinstance(field, drf_serializers.ManyRelatedField):
            model = field.child_relation.queryset.model
            result["additionalProps"] = {
                "model_name": model._meta.verbose_name_plural.replace(" ", "-"),
                "app_label": model._meta.app_label,
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
    """
    UiSchemaProcessor to account for custom field types and behaviors for Nautobot.
    """
    
    def _field_order(self):
        field_order = super()._field_order()
        serializer_field_order = getattr(self.serializer.Meta, "field_order", None)
        return serializer_field_order.keys() if serializer_field_order else field_order

    
    def get_ui_schema(self):
        ui_schema = super().get_ui_schema()
        serializer_ui_options = getattr(self.serializer.Meta, "ui_options", None)
        if not serializer_ui_options:
            return ui_schema
        
        if ui_schema.get("items"):
            ui_schema["items"]["ui:options"] = serializer_ui_options
        else:
            ui_schema["ui:options"] = serializer_ui_options
        return ui_schema
        
        
    def _get_all_ui_properties(self):
        ui_properties = super()._get_all_ui_properties()
        field_order = getattr(self.serializer.Meta, "field_order", None)
        if not field_order:
            return ui_properties

        grouping = {}
        for group_name, fields in field_order.items():
            fields_data = {name: ui_properties.get(name) for name in fields}
            if any(fields_data.values()):
                grouping[group_name] = fields_data
        return grouping

    # Commented Out for now
    # def _field_order(self) -> List[str]:
    #     """
    #     Overload the base which just returns `Meta.fields` and doesn't play nicely with "__all__".

    #     This instead calls `get_fields()` and returns the keys.
    #     """
    #     if self._is_list_serializer(self.serializer):
    #         fields = self.serializer.child.get_fields()
    #     else:
    #         fields = self.serializer.get_fields()

    #     field_names = list(fields)
    #     # FIXME(jathan): Correct the behavior introduced in #3500 by switching to `__all__` to
    #     # assert these get added at the end.
    #     bottom_fields = ["computed_fields", "custom_fields", "relationships"]
    #     for field_name in bottom_fields:
    #         if field_name in field_names:
    #             field_names.remove(field_name)
    #             field_names.append(field_name)

    #     return field_names


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

    def determine_view_options(self, request, view, serializer):
        """Determine view options that will be used for non-form display metadata."""
        view_options = {}
        list_display = []
        fields = []

        # FIXME(jathan): This mapping of fields and re-ordering things is currently a hack that MUST
        # be replaced by a central solution where field order is consistent and defined in one
        # place. All of the "bottom fields" stuff and coercion of ordering here will go away.
        processor = schema.ColumnProcessor(serializer, request.parser_context)
        field_map = dict(processor.fields)

        # TODO(jathan): For now, this is defined on the viewset. This is the cleanest since metadata
        # generation always gets the view instance.
        all_fields = list(field_map)
        list_display_fields = getattr(view, "list_display", None) or []

        # Explicitly order the "big ugly" fields to the bottom.
        # FIXME(jathan): Correct the behavior introduced in #3500 by switching to `__all__` to
        # assert these get added at the end.
        bottom_fields = ["computed_fields", "custom_fields", "relationships"]
        for field_name in bottom_fields:
            if field_name in all_fields:
                all_fields.remove(field_name)
                all_fields.append(field_name)
            if field_name in list_display_fields:
                list_display_fields.remove(field_name)
                list_display_fields.append(field_name)

        # Process the list_display fields first.
        for field_name in list_display_fields:
            field = field_map[field_name]
            column_data = processor._get_column_properties(field, field_name)
            list_display.append(column_data)
            fields.append(column_data)

        # Process the rest of the fields second.
        for field_name in all_fields:
            if field_name in list_display_fields:
                continue
            field = field_map[field_name]
            column_data = processor._get_column_properties(field, field_name)
            fields.append(column_data)

        view_options["list_display"] = list_display
        view_options["fields"] = fields

        return view_options

    def determine_metadata(self, request, view):
        """This is the metadata that gets returned on an `OPTIONS` request."""
        metadata = super().determine_metadata(request, view)

        # If there's a serializer, do the needful to bind the schema/uiSchema.
        if hasattr(view, "get_serializer"):
            serializer = view.get_serializer()
            metadata.update(
                {
                    "schema": NautobotSchemaProcessor(serializer, request.parser_context).get_schema(),
                    "uiSchema": NautobotUiSchemaProcessor(serializer, request.parser_context).get_ui_schema(),
                }
            )

        metadata["view_options"] = self.determine_view_options(request, view, serializer)

        return metadata
