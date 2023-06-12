import contextlib
from typing import Any, Dict, List

from django.core.exceptions import PermissionDenied
from django.http import Http404
import drf_react_template.schema_form_encoder as schema
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers as drf_serializers
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request
from rest_framework.relations import ManyRelatedField

from nautobot.core.templatetags.helpers import bettertitle


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
                    model_options = field.queryset.model._meta
                    result["required"] = field.required
                    # Custom Keyword: modelName and appLabel
                    # This Keyword represents the model name of the uuid model
                    # and appLabel represents the app_name of the model
                    result["modelName"] = model_options.model_name
                    result["appLabel"] = model_options.app_label
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

    def determine_view_options(self, request, serializer):
        """Determine view options that will be used for non-form display metadata."""
        list_display = []
        fields = []

        processor = NautobotColumnProcessor(serializer, request.parser_context)
        field_map = dict(serializer.fields)
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

        return {
            "retrieve": self.determine_detail_view_schema(serializer),
            "list_display_fields": list_display,
            "fields": fields,
        }

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
                    "uiSchema": ui_schema,
                }
            )

            metadata["view_options"] = self.determine_view_options(request, serializer)

        return metadata

    def restructure_view_config(self, view_config):
        """
        Restructure the view config by removing specific fields ("natural_key_slug", "url", "display", "status", "id")
        from the view config and adding standard fields ("id", "natural_key_slug", "url") to the first item's fields.

        This operation aims to establish a standardized and consistent way of displaying the fields "id", "natural_key_slug",
        and "url" within the view config.

        Example:
            >>> view_config = [
                {
                    Location: {fields: ["display", "name",...]},
                    Others: {fields: ["tenant", "tenant_group", "status"]}
                },
                ...
            ]
            >>> restructure_view_config(view_config)
            [
                {
                    Location: {fields: ["name","id","natural_key_slug","url"]},
                    Others: {fields: ["tenant", "tenant_group"]}
                },
                ...
            ]
        """

        # TODO(timizuo): Add a standardized way of handling `tenant` and `tags` fields, Possible should be on last items on second col.
        fields_to_remove = ["natural_key_slug", "url", "display", "status", "id"]
        fields_to_add = ["id", "natural_key_slug", "url"]

        for section_idx, section in enumerate(view_config):
            for idx, data in enumerate(section.items()):
                _, value = data
                for field in fields_to_remove:
                    if field in value["fields"]:
                        value["fields"].remove(field)
                if section_idx == 0 and idx == 0:
                    value["fields"].extend(fields_to_add)
        return view_config

    def get_m2m_and_non_m2m_fields(self, serializer):
        """
        Retrieve the many-to-many (m2m) fields and other non-m2m fields from the serializer.

        Returns:
            A tuple containing two lists: m2m_fields and non m2m fields.
                - m2m_fields: A list of dictionaries, each containing the name and label of an m2m field.
                - non_m2m_fields: A list of dictionaries, each containing the name and label of a non m2m field.
        """
        m2m_fields = []
        non_m2m_fields = []

        for field_name, field in serializer.fields.items():
            if isinstance(field, ManyRelatedField):
                m2m_fields.append({"name": field_name, "label": field.label or field_name})
            else:
                non_m2m_fields.append({"name": field_name, "label": field.label or field_name})

        return m2m_fields, non_m2m_fields

    def get_default_detail_view_config(self, serializer):
        """
        Generate detail view config for the view based on the serializer's fields.

        Examples:
            >>> SerializerDetailViewConfig(DeviceSerializer()).view_config().
            [
                {
                    Device: {
                        "fields": ["name", "subdevice_role", "height", "comments"...]
                    }
                },
                {
                    Tags: {
                        "fields": ["tags"]
                    }
                }
            ]

        Returns:
            A list representing the view config.
        """
        m2m_fields, other_fields = self.get_m2m_and_non_m2m_fields(serializer)
        model_verbose_name = serializer.Meta.model._meta.verbose_name
        return [
            {
                bettertitle(model_verbose_name): {
                    "fields": [field["name"] for field in other_fields],
                }
            },
            {field["label"]: {"fields": [field["name"]]} for field in m2m_fields},
        ]

    def determine_detail_view_schema(self, serializer):
        """Determine the layout option that would be used for the detail view"""
        if hasattr(serializer.Meta, "detail_view_config"):
            view_config = serializer.Meta.detail_view_config
        else:
            view_config = self.get_default_detail_view_config(serializer)
        return self.restructure_view_config(view_config)
