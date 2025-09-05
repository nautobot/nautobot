import csv
from io import StringIO
import json
import logging

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_TYPE

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
                current_dict[key] = None if value in [CSV_NO_OBJECT, CSV_NULL_TYPE] else value
            else:
                current_dict[key] = current_dict.get(key, {})
                insert_nested_dict(keys[1:], value, current_dict[key])

        result_dict = {}
        for original_key, original_value in data.items():
            split_keys = original_key.split("__")
            insert_nested_dict(split_keys, original_value, result_dict)

        return result_dict

    def _field_lookups_not_empty(self, field_lookups):
        """Check if all values of the field lookups dict are not all NoObject"""
        return any(value != CSV_NO_OBJECT for value in field_lookups.values())

    def _remove_object_not_found_values(self, data):
        """Remove all `CSV_NO_OBJECT` field lookups from the given data, and swap out `CSV_NULL_TYPE` and
        'CSV_NO_OBJECT' values for `None`.

        If all the lookups for a field are 'CSV_NO_OBJECT', it indicates that the field does not exist,
        and it needs to be removed to prevent unnecessary database queries.

        Args:
            data (dict): A dictionary containing field natural key lookups and their corresponding values.

        Returns:
            dict: A modified dictionary with field lookups of 'CSV_NO_OBJECT' values removed, and 'CSV_NULL_TYPE' and 'CSV_NO_OBJECT' swapped for `None`.
        """
        lookup_grouped_by_field_name = {}
        for lookup, lookup_value in data.items():
            field_name = lookup.split("__", 1)[0]
            lookup_grouped_by_field_name.setdefault(field_name, {}).update({lookup: lookup_value})

        # Ignore lookup groups which has all its values set to NoObject
        # These lookups fields do not exists
        data_without_missing_field_lookups_values = {
            lookup: lookup_value
            for lookup_group in lookup_grouped_by_field_name.values()
            for lookup, lookup_value in lookup_group.items()
            if self._field_lookups_not_empty(lookup_group)
        }

        return data_without_missing_field_lookups_values

    def _convert_m2m_dict_to_list_of_dicts(self, data, field):
        """
        Converts a nested dictionary into list of flat dictionaries for M2M serializer.

        Args:
            data (dict): Nested dictionary with comma-separated string values.
            field (str): Field name used in error messages.

        Returns:
            list: List of dictionaries, each containing one set of related values.

        Raises:
            ParseError: If the number of comma-separated values is inconsistent
                       across different keys.

        Examples:
            >>> data = {'manufacturer': {'name': 'Cisco,Cisco,Aruba'}, 'model': 'C9300,C9500,CX 6300'}
            >>> field = "device_type"
            >>> value = self.convert_m2m_dict_to_list_of_dicts(data, field)
            >>> value
            [
                {'manufacturer': {'name': 'Cisco'},'model': 'C9300'},
                {'manufacturer': {'name': 'Cisco'},'model': 'C9500'},
                {'manufacturer': {'name': 'Aruba'},'model': 'CX 6300'}
            ]
        """

        def flatten_dict(d, parent_key=""):
            """Flatten nested dictionary with __ separated keys"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}__{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key).items())
                else:
                    items.append((new_key, v.split(",")))
            return dict(items)

        flat_data = flatten_dict(data)

        # Convert dictionary to list of dictionaries
        values_count = {len(value) for value in flat_data.values()}
        if len(values_count) > 1:
            raise ParseError(f"Incorrect number of values provided for the {field} field")
        values_count = values_count.pop()
        return [
            self._group_data_by_field_name({key: value[i] for key, value in flat_data.items()})
            for i in range(values_count)
        ]

    def row_elements_to_data(self, counter, row, serializer):
        """
        Parse a single row of CSV data (represented as a dict) into a dict suitable for consumption by the serializer.

        TODO: it would be more elegant if our serializer fields knew how to deserialize the CSV data themselves;
        could we then literally have the parser just return list(reader) and not need this function at all?
        """
        data = {}
        valid_row_data = self._remove_object_not_found_values(row)
        fields_value_mapping = self._group_data_by_field_name(valid_row_data)
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
                if value:
                    # A list of related objects, represented as a list of composite-keys
                    if isinstance(value, str):
                        value = value.split(",")
                    # A dictionary of fields identifying the objects
                    elif isinstance(value, dict):
                        value = self._convert_m2m_dict_to_list_of_dicts(value, key)
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
                from nautobot.extras.api.serializers import ObjectMetadataValueJSONField

                if isinstance(serializer_field, ObjectMetadataValueJSONField):
                    # Do not split value into a list or dicts when it comes to the value of ObjectMetadata
                    # we want to store it as bare ints/strings
                    pass
                elif value is not None:
                    if value.startswith(("{", "[")):
                        value = json.loads(value)
                    else:
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
