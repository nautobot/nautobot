from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.db.models import ManyToManyField
from django.http import Http404
import drf_react_template.schema_form_encoder as schema
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request


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
    """
    UiSchemaProcessor to account for custom field types and behaviors for Nautobot.
    """

    def _field_order(self) -> List[str]:
        """
        Overload the base which just returns `Meta.fields` and doesn't play nicely with "__all__".

        This instead calls `get_fields()` and returns the keys.
        """
        if self._is_list_serializer(self.serializer):
            fields = self.serializer.child.get_fields()
        else:
            fields = self.serializer.get_fields()

        field_names = list(fields)

        return field_names


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

        processor = schema.ColumnProcessor(serializer, request.parser_context)
        field_map = dict(processor.fields)
        all_fields = list(field_map)
        list_display_fields = getattr(serializer.Meta, "list_display", None) or []

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
            if field_name in list_display_fields:
                continue
            try:
                field = field_map[field_name]
            except KeyError:
                continue  # Ignore unknown fields.
            column_data = processor._get_column_properties(field, field_name)
            fields.append(column_data)

        view_options["list_display"] = list_display
        view_options["fields"] = fields

        return view_options
    
    def get_detail_view_field_link(self, instance):
        return {
            "app_label": instance._meta.app_label,
            "model_name": instance._meta.model_name,
            "id":  instance.pk,
        }

    def build_detail_view_field_for_list(self, model_instance, field_name):
        field = model_instance._meta.get_field(field_name)
        field_verbose_name = field.verbose_name
        field_label = field_verbose_name.capitalize() if field_verbose_name.islower() else field_verbose_name
        field_value = getattr(model_instance, field_name, None)
        link = None
        color = None

        is_related_field = field.is_relation
        if is_related_field:
            if isinstance(field, ManyToManyField):
                # TODO: Account for M2M fields
                pass
            elif field_value:
                link = self.get_detail_view_field_link(field_value)
                color = getattr(field_value, "color", None)
                field_value = getattr(field_value, "display", str(field_value))

        return {
            "label": field_label,
            "value": field_value,
            "link": link,
            "color": color
        }
    
    def build_detail_view_field_for_table(self, model_instance, table_props):
        pass
    
    def build_detail_view_field_for_box(self, model_instance, field_name):
        return getattr(model_instance, field_name, None) 
    
    def build_detail_view_group_data(self, data, model_instance):
        template = data.get("template", "list")
        group_data = {
            "template": template,
            "template_actions": data.get("template_actions", []),
        }
        
        if template == "list":
            group_data["fields"] = [
                self.build_detail_view_field_for_list(model_instance, field_name) for field_name in data["fields"]
            ]
        elif template == "table":
            group_data["table_data"] = self.build_detail_view_field_for_table(model_instance, data["table"])
        else:
            group_data["field"] = self.build_detail_view_field_for_box(model_instance, data["field"])
    
        return group_data

    def build_detail_view_columns(self, model_instance, grouping_data, column):
        return {
            "col": column,
            "groups": {
                group_name: self.build_detail_view_group_data(group_data, model_instance)
                for group_name, group_data in grouping_data.items()
                if group_data.get("col") == column
            },
        }

    def determine_detail_view_schema(self, request, view, serializer):
        """Build Schema for UI detail view"""
        schema = {}
        # Todo: Account for models without a detail schema set on the serializer
        detail_view_schema = getattr(serializer.Meta, "detail_view_schema", None)
        if not detail_view_schema:
            return schema

        model = getattr(serializer.Meta, "model", None)
        query_filter_params = request.parser_context["kwargs"]
        try:
            model_instance = model.objects.get(**query_filter_params)
        except model.DoesNotExist:
            return schema

        columns = detail_view_schema.get("columns", 1)
        schema["column_no"] = columns
        grouping_data = detail_view_schema.get("grouping", {})
        schema["columns"] = {
            col_no + 1: self.build_detail_view_columns(model_instance, grouping_data, col_no+1)
            for col_no in range(columns)
        }
        return schema

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
            metadata["detail_view_schema"] = self.determine_detail_view_schema(request, view, serializer)

        return metadata
