import csv
from io import StringIO
import json
import logging

from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from nautobot.core.models.utils import deconstruct_composite_key


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
            raise ParseError("No serializer_class was provided by the parser_context")
        if serializer_class is None:
            raise ParseError("Serializer class for this parser_context is None, unable to proceed")

        serializer = serializer_class(context={"request": parser_context.get("request", None), "depth": 0})

        try:
            text = stream.read().decode(encoding)
            reader = csv.DictReader(StringIO(text))

            data = []
            for counter, row in enumerate(reader, start=1):
                data.append(self.row_elements_to_data(counter, row, serializer=serializer))

            if "pk" in parser_context.get("kwargs", {}):
                # Single-object update, not bulk update - strip it so that we get the expected input and return format
                data = data[0]
            # Note that we can't distinguish between single-create and bulk-create with a list of one object,
            # as both would have the same CSV representation. Therefore create via CSV **always** acts as bulk-create,
            # and the response will always be a list of created objects, never a single object

            if settings.DEBUG:
                logger.debug("CSV loaded into data:\n%s", json.dumps(data, indent=2))
            return data
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(str(exc)) from exc

    def row_elements_to_data(self, counter, row, serializer):
        """
        Parse a single row of CSV data (represented as a dict) into a dict suitable for consumption by the serializer.

        TODO: it would be more elegant if our serializer fields knew how to deserialize the CSV data themselves;
        could we then literally have the parser just return list(reader) and not need this function at all?
        """
        data = {}
        for column, key in enumerate(row.keys(), start=1):
            if not key:
                raise ParseError(f"Row {counter}: Column {column}: missing/empty header for this column")

            value = row[key]
            if key.startswith("cf_"):
                # Custom field
                if value == "":
                    value = None
                data.setdefault("custom_fields", {})[key[3:]] = value
                continue

            serializer_field = serializer.fields.get(key, None)
            if serializer_field is None:
                # The REST API normally just ignores any columns the serializer doesn't understand
                logger.debug('Skipping unknown column "%s"', key)
                continue

            if serializer_field.read_only and key != "id":
                # Deserializing read-only fields is tricky, especially for things like SerializerMethodFields that
                # can potentially render as anything. We don't strictly need such fields (except "id" for bulk PATCH),
                # so let's just skip it.
                continue

            if isinstance(serializer_field, serializers.ManyRelatedField):
                # A list of related objects, represented as a list of composite-keys
                if value:
                    related_model = serializer_field.child_relation.get_queryset().model
                    value = [self.get_composite_key_dict(slug, related_model) for slug in value.split(",")]
                else:
                    value = []
            elif isinstance(serializer_field, serializers.RelatedField):
                # A single related object, represented by its composite-key
                if value:
                    related_model = serializer_field.get_queryset().model
                    value = self.get_composite_key_dict(value, related_model)
                else:
                    value = None
            elif isinstance(serializer_field, (serializers.ListField, serializers.MultipleChoiceField)):
                if value:
                    value = value.split(",")
                else:
                    value = []
            elif isinstance(serializer_field, (serializers.DictField, serializers.JSONField)):
                # We currently only store lists or dicts in JSONFields, never bare ints/strings.
                # On the CSV write side, we only render dicts to JSON
                if "{" in value or "[" in value:
                    value = json.loads(value)
                elif value:
                    value = value.split(",")
                    try:
                        # We have some cases where it's a list of integers, such as in RackReservation.units
                        value = [int(v) for v in value]
                    except ValueError:
                        # Guess not!
                        pass

            # CSV doesn't provide a ready distinction between blank and null, so in this case we have to pick one.
            # This does mean that for a nullable AND blankable field, there's no way for CSV to set it to blank string.
            # See corresponding logic in NautobotCSVRenderer.
            if value == "" and serializer_field.allow_null:
                value = None

            data[key] = value

        return data

    def get_composite_key_dict(self, composite_key, model):
        """
        Get the data dictionary corresponding to the given composite key list or string for the given model.
        """
        if not composite_key:
            return None
        if model._meta.label_lower == "contenttypes.contenttype":
            # Our ContentTypeField just uses the "app_label.model" string to look up ContentTypes, rather than the
            # actual ([app_label, model]) natural key for ContentType.
            return composite_key
        if model._meta.label_lower == "auth.group":
            # auth.Group is a base Django model and so doesn't implement our natural_key_args_to_kwargs() method.
            return {"name": deconstruct_composite_key(composite_key)}
        if hasattr(model, "natural_key_args_to_kwargs"):
            return model.natural_key_args_to_kwargs(deconstruct_composite_key(composite_key))
        logger.error("%s doesn't implement natural_key_args_to_kwargs()", model.__name__)
        return {"pk": composite_key}
