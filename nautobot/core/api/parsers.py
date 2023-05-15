import csv
from io import StringIO
import json
import logging

from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from nautobot.core.models.utils import deconstruct_natural_key_slug


logger = logging.getLogger(__name__)


class NautobotCSVParser(BaseParser):
    """Counterpart to NautobotCSVRenderer - import CSV data."""

    media_type = "text/csv"

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", "UTF-8")
        try:
            if "serializer_class" in parser_context:
                # UI bulk-import case
                serializer_class = parser_context["serializer_class"]
            else:
                # REST API case
                serializer_class = parser_context["view"].get_serializer_class()
        except (KeyError, AttributeError):
            logger.error("Unable to find serializer_class for the view?")
            return None
        if serializer_class is None:
            logger.error("No serializer_class for the view?")
            return None

        serializer = serializer_class(context={"request": parser_context.get("request", None)})

        try:
            text = stream.read().decode(encoding)
            reader = csv.DictReader(StringIO(text))

            data = []
            for row in reader:
                data.append(self.row_elements_to_data(row, serializer=serializer))

            if "pk" in parser_context.get("kwargs", {}):
                # Single-object update, not bulk update - strip it so that we get the expected input and return format
                data = data[0]
            # Note that we can't distinguish between single-create and bulk-create with a list of one object,
            # as both would have the same CSV representation. Therefore create via CSV **always** acts as bulk-create,
            # and the response will always be a list of created objects, never a single object

            if settings.DEBUG:
                logger.debug("CSV loaded into data:\n%s", json.dumps(data, indent=2))
            return data
        except Exception as exc:
            raise ParseError(str(exc)) from exc

    def row_elements_to_data(self, row, serializer):
        """
        Parse a single row of CSV data (represented as a dict) into a dict suitable for consumption by the serializer.

        TODO: it would be more elegant if our serializer fields knew how to deserialize the CSV data themselves;
        could we then literally have the parser just return list(reader) and not need this function at all?
        """
        data = {}
        for key, value in row.items():
            if key.startswith("cf_"):
                # Custom field
                if value == "":
                    value = None
                data.setdefault("custom_fields", {})[key[3:]] = value
                continue

            serializer_field = serializer.fields.get(key)
            if not serializer_field:
                raise KeyError(key)

            if serializer_field.read_only and key != "id":
                # Deserializing read-only fields is tricky, especially for things like SerializerMethodFields that
                # can potentially render as anything. We don't strictly need such fields (except "id" for bulk PATCH),
                # so let's just skip it.
                continue

            if isinstance(serializer_field, serializers.ManyRelatedField):
                # A list of related objects, represented as a list of natural-key-slugs
                if value:
                    related_model = serializer_field.child_relation.get_queryset().model
                    value = [self.get_natural_key_dict(slug, related_model) for slug in json.loads(value)]
                else:
                    value = []
            elif isinstance(serializer_field, serializers.RelatedField):
                # A single related object, represented by its natural-key-slug
                if value:
                    related_model = serializer_field.get_queryset().model
                    value = self.get_natural_key_dict(value, related_model)
                else:
                    value = None
            elif isinstance(
                serializer_field,
                (serializers.DictField, serializers.JSONField, serializers.ListField, serializers.MultipleChoiceField),
            ):
                if value != "":
                    value = json.loads(value)

            if value == "" and serializer_field.allow_null:
                value = None

            data[key] = value

        return data

    def get_natural_key_dict(self, natural_key_slug, model):
        """
        Get the data dictionary corresponding to the given natural key list or string for the given model.
        """
        if not natural_key_slug:
            return None
        if model._meta.label_lower == "contenttypes.contenttype":
            # Our ContentTypeField just uses the "app_label.model" string to look up ContentTypes, rather than the
            # actual ([app_label, model]) natural key for ContentType.
            return natural_key_slug
        if model._meta.label_lower == "auth.group":
            # auth.Group is a base Django model and so doesn't implement our natural_key_slug queryset filter
            return {"name": natural_key_slug}
        if hasattr(model, "natural_key_args_to_kwargs"):
            return model.natural_key_args_to_kwargs(deconstruct_natural_key_slug(natural_key_slug))
        logger.error("%s doesn't implement natural_key_args_to_kwargs()", model.__name__)
        return {"pk": natural_key_slug}
