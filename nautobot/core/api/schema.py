import logging
import re

from drf_spectacular.openapi import AutoSchema
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

    def get_operation_id(self):
        """Extend the base method to handle Nautobot's REST API bulk operations.

        Without this extension, every one of our ModelViewSet classes will result in drf-spectacular complaining
        about operationId collisions, e.g. between DELETE /api/dcim/devices/ and DELETE /api/dcim/devices/<pk>/ would
        both get resolved to the same "dcim_devices_destroy" operation-id and this would make drf-spectacular complain.

        With this extension, the bulk endpoints automatically get a different operation-id from the non-bulk endpoints.
        """
        if hasattr(self.view, "action") and self.view.action in ["bulk_update", "bulk_partial_update", "bulk_destroy"]:
            # Same basic sequence of calls as AutoSchema.get_operation_id,
            # except we use "self.view.action" instead of "self.method_mapping[self.method]" to get the action verb
            tokenized_path = self._tokenize_path()
            tokenized_path = [t.replace("-", "_") for t in tokenized_path]

            action = self.view.action

            if not tokenized_path:
                tokenized_path.append("root")
            if re.search(r"<drf_format_suffix\w*:\w+>", self.path_regex):
                tokenized_path.append("formatted")

            return "_".join(tokenized_path + [action])

        # For all other view actions, operation-id is the same as in the base class
        return super().get_operation_id()

    def get_request_serializer(self):
        """Return the request serializer (used for parsing the request payload) for this endpoint.

        We override the default drf-spectacular behavior for the case where the endpoint describes a write request
        with required data (PATCH, POST, PUT). In those cases we replace FooSerializer with a dynamically-defined
        WritableFooSerializer class in order to more accurately represent the available options on write.
        """
        serializer = super().get_request_serializer()

        if serializer is not None and self.method in ["PATCH", "POST", "PUT"]:
            writable_class = self.get_writable_class(serializer)
            if writable_class is not None:
                if hasattr(serializer, "child"):
                    child_serializer = self.get_writable_class(serializer.child)
                    serializer = writable_class(child=child_serializer)
                else:
                    serializer = writable_class()

        return serializer

    writable_serializers = {}
    """Cache of existing dynamically-defined WritableFooSerializer classes."""

    def get_writable_class(self, serializer):
        """
        Given a FooSerializer class, look up or construct a corresponding WritableFooSerializer class if necessary.

        If no WritableFooSerializer class is needed, returns None instead.
        """
        properties = {}
        # Does this serializer have any fields of certain special types?
        # TODO why these specific types?
        fields = {} if hasattr(serializer, "child") else serializer.fields
        for child_name, child in fields.items():
            if isinstance(child, (ChoiceField, WritableNestedSerializer)):
                properties[child_name] = None
            elif isinstance(child, ManyRelatedField) and isinstance(child.child_relation, SerializedPKRelatedField):
                properties[child_name] = None

        if not properties:
            # There's nothing about this serializer that requires a special WritableSerializer class to be defined.
            return None

        # Have we already created a WritableFooSerializer class or do we need to do so now?
        if not isinstance(serializer, tuple(self.writable_serializers)):
            # We need to create a new class to use
            writable_name = "Writable" + type(serializer).__name__
            # If the original serializer class has a Meta, make sure we set Meta.ref_name appropriately
            meta_class = getattr(type(serializer), "Meta", None)
            if meta_class:
                ref_name = "Writable" + self.get_serializer_ref_name(serializer)
                writable_meta = type("Meta", (meta_class,), {"ref_name": ref_name})
                properties["Meta"] = writable_meta

            # Define and cache a new WritableFooSerializer class
            self.writable_serializers[type(serializer)] = type(writable_name, (type(serializer),), properties)

        writable_class = self.writable_serializers[type(serializer)]
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
