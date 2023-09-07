import csv
from io import StringIO
import json
import logging

from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser


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

    def _group_data_by_field_name(self, data):
        """
        Converts a dictionary with flat keys separated by '__' into a nested dictionary structure suitable for serialization.

        Example:
            Input:
                {
                    'type': 'virtual',
                    'name': 'Interface 4',
                    'device__name': 'Device 1',
                    'device__tenant__name': '',
                    'device__location': 'Test+Location+1',
                    'status': 'Active',
                }

            Output:
            {
                'type': 'virtual',
                'name': 'Interface 4',
                'device': {
                    'name': 'Device 1',
                    'location': 'Test+Location+1',
                    "tenant":{
                        "name": "",
                    }
                },
                'status': 'Active'
            }
        """

        def insert_nested_dict(keys, value, current_dict):
            key = keys[0]
            if len(keys) == 1:
                current_dict[key] = value
            else:
                current_dict[key] = current_dict.get(key, {})
                insert_nested_dict(keys[1:], value, current_dict[key])

        result_dict = {}
        for original_key, original_value in data.items():
            split_keys = original_key.split("__")
            insert_nested_dict(split_keys, original_value, result_dict)

        return result_dict

    def row_elements_to_data(self, counter, row, serializer):
        """
        Parse a single row of CSV data (represented as a dict) into a dict suitable for consumption by the serializer.

        TODO: it would be more elegant if our serializer fields knew how to deserialize the CSV data themselves;
        could we then literally have the parser just return list(reader) and not need this function at all?
        """
        data = {}
        fields_value_mapping = self._group_data_by_field_name(row)
        for column, key in enumerate(fields_value_mapping.keys(), start=1):
            if not key:
                raise ParseError(f"Row {counter}: Column {column}: missing/empty header for this column")

            value = fields_value_mapping[key]
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
                    value = value.split(",")
                else:
                    value = []
            elif isinstance(serializer_field, serializers.RelatedField):
                # A single related object, represented by its composite-key
                if value:
                    pass
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
