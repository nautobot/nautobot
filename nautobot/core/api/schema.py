import logging
import re

from drf_spectacular.contrib.django_filters import DjangoFilterExtension
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import (
    build_array_type,
    build_basic_type,
    build_media_type_object,
    get_doc,
    is_serializer,
    list_hash,
)
from drf_spectacular.serializers import PolymorphicProxySerializerExtension
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from rest_framework.relations import ManyRelatedField

from nautobot.core.api import (
    ChoiceField,
    SerializedPKRelatedField,
    WritableNestedSerializer,
)

logger = logging.getLogger(__name__)


class NautobotAutoSchema(AutoSchema):
    """Nautobot-specific extensions to drf-spectacular's AutoSchema."""

    custom_actions = ["bulk_update", "bulk_partial_update", "bulk_destroy"]

    # Primarily, method_mapping is used to map HTTP method verbs to viewset method names,
    # which doesn't account for the fact that with our custom actions there are multiple viewset methods per verb,
    # hence why we have to override get_operation_id() below.
    # Secondarily, drf-spectacular uses method_mapping.values() to identify which methods are view methods,
    # so need to make sure these methods are represented as values in the mapping even if not under the actual verbs.
    method_mapping = AutoSchema.method_mapping.copy()
    method_mapping.update(
        {
            "_put": "bulk_update",
            "_patch": "bulk_partial_update",
            "_delete": "bulk_destroy",
        }
    )

    @property
    def is_bulk_action(self):
        """Custom property for convenience."""
        return hasattr(self.view, "action") and self.view.action in self.custom_actions

    @property
    def is_partial_action(self):
        """Custom property for convenience."""
        return hasattr(self.view, "action") and self.view.action in ["partial_update", "bulk_partial_update"]

    def _get_paginator(self):
        """Nautobot's custom bulk operations, even though they return a list of records, are NOT paginated."""
        if self.is_bulk_action:
            return None
        return super()._get_paginator()

    def get_description(self):
        """
        Get the appropriate description for a given API endpoint.

        By default, if a specific action doesn't have its own docstring, and neither does the view class,
        drf-spectacular will walk up the MRO of the view class until it finds a docstring, and use that.
        Most of our viewsets (for better or for worse) do not have docstrings, and so it'll find and use the generic
        docstring of the `NautobotModelViewSet` class, which isn't very useful to the end user. Instead of doing that,
        we only use the docstring of the view itself (ignoring its parent class docstrings), or if none exists, we
        make an attempt at rendering a basically accurate default description.
        """
        action_or_method = getattr(self.view, getattr(self.view, "action", self.method.lower()), None)
        action_doc = get_doc(action_or_method)
        if action_doc:
            return action_doc

        if self.view.__doc__:
            view_doc = get_doc(self.view.__class__)
            if view_doc:
                return view_doc

        # Fall back to a generic default description
        if hasattr(self.view, "queryset") and self.method.lower() in self.method_mapping:
            action = self.method_mapping[self.method.lower()].replace("_", " ").capitalize()
            model_name = self.view.queryset.model._meta.verbose_name
            if action == "Create":
                return f"{action} one or more {model_name} objects."
            if "{id}" in self.path:
                return f"{action} a {model_name} object."
            return f"{action} a list of {model_name} objects."

        # Give up
        return super().get_description()

    def get_filter_backends(self):
        """Nautobot's custom bulk operations, even though they return a list of records, are NOT filterable."""
        if self.is_bulk_action:
            return []
        return super().get_filter_backends()

    def get_operation(self, *args, **kwargs):
        operation = super().get_operation(*args, **kwargs)
        # drf-spectacular never generates a requestBody for DELETE operations, but our bulk-delete operations need one
        if operation is not None and "requestBody" not in operation and self.is_bulk_action and self.method == "DELETE":
            # based on drf-spectacular's `_get_request_body()`, `_get_request_for_media_type()`,
            # `_unwrap_list_serializer()`, and `_get_request_for_media_type()` methods
            request_serializer = self.get_request_serializer()

            # We skip past a number of checks from the aforementioned private methods, as this is a very specific case
            component = self.resolve_serializer(request_serializer.child, "request")

            operation["requestBody"] = {
                "content": {
                    media_type: build_media_type_object(build_array_type(component.ref))
                    for media_type in self.map_parsers()
                },
                "required": True,
            }

        if operation is not None and "parameters" in operation:
            for param in operation["parameters"]:
                # Inject a custom description for the "id" parameter since ours has custom lookup behavior.
                if param["name"] == "id" and "description" not in param:
                    param["description"] = "Unique object identifier, either a UUID primary key or a composite key."
            if self.method == "GET":
                if not any(param["name"] == "depth" for param in operation["parameters"]):
                    operation["parameters"].append(
                        {
                            "in": "query",
                            "name": "depth",
                            "required": False,
                            "description": "Serializer Depth",
                            "schema": {"type": "integer", "minimum": 0, "maximum": 10, "default": 1},
                        }
                    )
                if not any(param["name"] == "exclude_m2m" for param in operation["parameters"]):
                    operation["parameters"].append(
                        {
                            "in": "query",
                            "name": "exclude_m2m",
                            "required": False,
                            "description": "Exclude many-to-many fields from the response",
                            "schema": {"type": "boolean", "default": False},
                        }
                    )
                # TODO: add "include" parameter to the schema where relevant - nautobot/nautobot#685
        return operation

    def get_operation_id(self):
        """Extend the base method to handle Nautobot's REST API bulk operations.

        Without this extension, every one of our ModelViewSet classes will result in drf-spectacular complaining
        about operationId collisions, e.g. between DELETE /api/dcim/devices/ and DELETE /api/dcim/devices/<pk>/ would
        both get resolved to the same "dcim_devices_destroy" operation-id and this would make drf-spectacular complain.

        With this extension, the bulk endpoints automatically get a different operation-id from the non-bulk endpoints.
        """
        if self.is_bulk_action:
            # Same basic sequence of calls as AutoSchema.get_operation_id,
            # except we use "self.view.action" instead of "self.method_mapping[self.method]" to get the action verb
            tokenized_path = self._tokenize_path()
            tokenized_path = [t.replace("-", "_") for t in tokenized_path]

            action = self.view.action

            if not tokenized_path:
                tokenized_path.append("root")
            if re.search(r"<drf_format_suffix\w*:\w+>", self.path_regex):
                tokenized_path.append("formatted")

            return "_".join([*tokenized_path, action])

        # For all other view actions, operation-id is the same as in the base class
        return super().get_operation_id()

    def get_request_serializer(self):
        """
        Return the request serializer (used for describing/parsing the request payload) for this endpoint.

        We override the default drf-spectacular behavior for the case where the endpoint describes a write request
        with required data (PATCH, POST, PUT). In those cases we replace FooSerializer with a dynamically-defined
        WritableFooSerializer class in order to more accurately represent the available options on write.

        We also override for the case where the endpoint is one of Nautobot's custom bulk API endpoints, which
        require a list of serializers as input, rather than a single one.
        """
        serializer = super().get_request_serializer()

        # For bulk operations, make sure we use a "many" serializer.
        many = self.is_bulk_action
        partial = self.is_partial_action

        if serializer is not None and self.method in ["PATCH", "POST", "PUT"]:
            writable_class = self.get_writable_class(serializer, bulk=many)
            if writable_class is not None:
                if hasattr(serializer, "child"):
                    child_serializer = self.get_writable_class(serializer.child, bulk=many)
                    serializer = writable_class(child=child_serializer, many=many, partial=partial)
                else:
                    serializer = writable_class(many=many, partial=partial)

        return serializer

    def get_response_serializers(self):
        """
        Return the response serializer (used for describing the response payload) for this endpoint.

        We override the default drf-spectacular behavior for the case where the endpoint describes a write request
        to a bulk endpoint, which returns a list of serializers, rather than a single one.
        """
        response_serializers = super().get_response_serializers()

        if self.is_bulk_action:
            if is_serializer(response_serializers):
                return type(response_serializers)(many=True)

        return response_serializers

    # Cache of existing dynamically-defined WritableFooSerializer classes.
    writable_serializers = {}

    def get_writable_class(self, serializer, bulk=False):
        """
        Given a FooSerializer instance, look up or construct a [Bulk]WritableFooSerializer class if necessary.

        If no [Bulk]WritableFooSerializer class is needed, returns None instead.
        """
        properties = {}
        # Does this serializer have any fields of certain special types?
        # These are the field types that are asymmetric between request (write) and response (read); if any such fields
        # are present, we should generate a distinct WritableFooSerializer to reflect that asymmetry in the schema.
        fields = {} if hasattr(serializer, "child") else serializer.fields
        for child_name, child in fields.items():
            # Don't consider read_only fields (since we're planning specifically for the writable serializer).
            if child.read_only:
                continue

            if isinstance(child, (ChoiceField, WritableNestedSerializer)):
                properties[child_name] = None
            elif isinstance(child, ManyRelatedField) and isinstance(child.child_relation, SerializedPKRelatedField):
                properties[child_name] = None

        if bulk:
            # The "id" field is always different in bulk serializers
            properties["id"] = None

        if not properties:
            # There's nothing about this serializer that requires a special WritableSerializer class to be defined.
            return None

        # Have we already created a [Bulk]WritableFooSerializer class or do we need to do so now?
        writable_name = "Writable" + type(serializer).__name__
        if bulk:
            writable_name = f"Bulk{writable_name}"
        if writable_name not in self.writable_serializers:
            # We need to create a new class to use
            # If the original serializer class has a Meta, make sure we set Meta.ref_name appropriately
            meta_class = getattr(type(serializer), "Meta", None)
            if meta_class:
                ref_name = "Writable" + self.get_serializer_ref_name(serializer)
                if bulk:
                    ref_name = f"Bulk{ref_name}"
                writable_meta = type("Meta", (meta_class,), {"ref_name": ref_name})
                properties["Meta"] = writable_meta

            # Define and cache a new [Bulk]WritableFooSerializer class
            if bulk:

                def get_fields(self):
                    """For Nautobot's bulk_update/partial_update/delete APIs, the `id` field is mandatory."""
                    new_fields = {}
                    for name, field in type(serializer)().get_fields().items():
                        if name == "id":
                            field.read_only = False
                            field.required = True
                        new_fields[name] = field
                    return new_fields

                properties["get_fields"] = get_fields

            self.writable_serializers[writable_name] = type(writable_name, (type(serializer),), properties)

        writable_class = self.writable_serializers[writable_name]
        return writable_class

    def get_serializer_ref_name(self, serializer):
        """
        Get the serializer's ref_name Meta attribute if set, or else derive a ref_name automatically.

        Based on drf_yasg.utils.get_serializer_ref_name().
        """
        serializer_meta = getattr(serializer, "Meta", None)
        if hasattr(serializer_meta, "ref_name"):
            return serializer_meta.ref_name
        serializer_name = type(serializer).__name__
        if serializer_name == "NestedSerializer" and isinstance(serializer, serializers.ModelSerializer):
            return None
        ref_name = serializer_name
        if ref_name.endswith("Serializer"):
            ref_name = ref_name[: -len("Serializer")]
        return ref_name

    def resolve_serializer(self, serializer, direction, bypass_extensions=False):
        """
        Re-add required `id` field on bulk_partial_update action.

        drf-spectacular clears the `required` list for any partial serializers in its `_map_basic_serializer()`,
        but Nautobot bulk partial updates require the `id` field to be specified for each object to update.
        """
        component = super().resolve_serializer(serializer, direction, bypass_extensions)
        if (
            component
            and component.schema is not None
            and self.is_bulk_action
            and self.is_partial_action
            and direction == "request"
        ):
            component.schema["required"] = ["id"]
        return component

    def _get_serializer_field_meta(self, field, direction):
        """Fix for ChoiceField that sets the default value's type to match the schema returned in the ChoiceFieldFix extension."""
        meta = super()._get_serializer_field_meta(field, direction)
        if isinstance(field, ChoiceField) and "default" in meta and direction == "request":
            meta["default"] = field.default

        return meta


class NautobotFilterExtension(DjangoFilterExtension):
    """
    Because drf-spectacular does extension registration by exact classpath matches, since we use a custom subclass
    of django_filters.rest_framework.DjangoFilterBackend, we have to point drf-spectacular to our subclass since the
    parent class isn't directly in use and therefore doesn't get extended??
    """

    target_class = "nautobot.core.api.filter_backends.NautobotFilterBackend"


class NautobotPolymorphicProxySerializerExtension(PolymorphicProxySerializerExtension):
    """
    Extend the PolymorphicProxySerializerExtension to cover Nautobot's PolymorphicProxySerializer class.
    """

    target_class = "nautobot.core.api.serializers.PolymorphicProxySerializer"


class ChoiceFieldFix(OpenApiSerializerFieldExtension):
    """
    Schema field fix for ChoiceField fields.

    These are asymmetric, taking a literal value on write but returning a dict of {value, label} on read.

    If we have two models that both have ChoiceFields with the same exact set of choices, drf-spectacular will
    complain about this with a warning like:

        enum naming encountered a non-optimally resolvable collision for fields named "type"

    This happens for a number of our fields already. The workaround is to explicitly declare an enum name for each
    such colliding serializer field under `settings.SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]`, for example:

        "CableTypeChoices": "nautobot.dcim.choices.CableTypeChoices",
    """

    target_class = "nautobot.core.api.fields.ChoiceField"

    def map_serializer_field(self, auto_schema, direction):
        """
        Define the OpenAPI schema for a given ChoiceField (self.target) for the given request/response direction.
        """
        choices = self.target._choices

        value_type = "string"
        # IPAddressVersionChoices and RackWidthChoices are int values, not strings
        if all(isinstance(x, int) for x in [c for c in list(choices.keys()) if c is not None]):
            value_type = "integer"
        # I don't think we have any of these left in the code base at present,
        # but historically in NetBox there were ChoiceFields with boolean values
        if all(isinstance(x, bool) for x in [c for c in list(choices.keys()) if c is not None]):
            value_type = "boolean"

        if direction == "request":
            return {
                "type": value_type,
                "enum": list(choices.keys()),
                # Used to deduplicate enums with the same set of choices, since drf-spectacular 0.27.2
                "x-spec-enum-id": list_hash([(k, v) for k, v in choices.items() if k not in ("", None)]),
            }
        else:
            return {
                "type": "object",
                "properties": {
                    "value": {
                        "type": value_type,
                        "enum": list(choices.keys()),
                    },
                    "label": {
                        "type": "string",
                        "enum": list(choices.values()),
                    },
                },
            }


class SerializedPKRelatedFieldFix(OpenApiSerializerFieldExtension):
    """
    Schema field fix for SerializedPKRelatedField fields.
    """

    target_class = "nautobot.core.api.fields.SerializedPKRelatedField"

    def map_serializer_field(self, auto_schema, direction):
        """
        On requests, require PK only; on responses, represent the entire nested serializer.
        """
        return auto_schema._map_serializer(self.target.serializer, direction)


class EmailFieldFix(OpenApiSerializerFieldExtension):
    """Fix invalid schema for EmailField when default is an empty string."""

    target_class = "rest_framework.serializers.EmailField"

    def map_serializer_field(self, auto_schema, direction):
        email_schema = build_basic_type(OpenApiTypes.EMAIL)
        str_schema = build_basic_type(OpenApiTypes.STR)
        auto_schema._insert_field_validators(self.target, email_schema)
        auto_schema._insert_field_validators(self.target, str_schema)
        email_schema.pop("format", None)
        if self.target.default == "":
            return {
                "oneOf": [
                    str_schema,
                    email_schema,
                ]
            }
        else:
            return email_schema
