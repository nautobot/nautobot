import csv
from io import StringIO
import json
import logging
import re

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser
import yaml

from nautobot.core.api.constants import (
    IMPORT_DOCUMENT_MATCH_FIELDS_KEY,
    IMPORT_DOCUMENT_MODEL_KEY,
    IMPORT_DOCUMENT_RECORDS_KEY,
    IMPORT_DOCUMENT_VERSION,
    IMPORT_DOCUMENT_VERSION_KEY,
)
from nautobot.core.api.utils import nest_flat_dict
from nautobot.core.constants import CSV_NO_OBJECT, CSV_NULL_SENTINELS

logger = logging.getLogger(__name__)


def read_import_text(stream, parser_context):
    """Read a parser's input stream as text, decoding it and stripping any leading byte-order mark.

    A BOM would otherwise corrupt the first cell/key of the file (defeating CSV directive detection, or
    silently mangling the first header name).
    """
    text = stream.read()
    if isinstance(text, bytes):
        text = text.decode(parser_context.get("encoding", "UTF-8"))
    return text.removeprefix("\ufeff")


def get_serializer_from_parser_context(parser_context):
    """Resolve the serializer class from a DRF parser_context and instantiate it at depth 0."""
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

    return serializer_class(context={"request": parser_context.get("request", None), "depth": 0})


class NautobotCSVParser(BaseParser):
    """Counterpart to NautobotCSVRenderer - import CSV data."""

    media_type = "text/csv"

    IMPORT_DIRECTIVE_MARKER = "nautobot-import:"
    SUPPORTED_IMPORT_DIRECTIVES = ("match_fields",)

    @classmethod
    def parse_directive_cell(cls, cell):
        """
        Parse a directive cell such as `# nautobot-import: match_fields=name serial` into a dict of directives.

        Rows whose first cell starts with `#` but doesn't contain the `nautobot-import:` marker are ordinary
        comments and parse to an empty dict. Within a directive, entries are separated by semicolons and the
        values of an entry are separated by spaces (or semicolons/commas); commas are avoided as the primary
        separator so that the directive stays in a single cell through spreadsheet round-trips.

        Returns:
            (dict): The parsed directives, e.g. `{"match_fields": ["name", "serial"]}`

        Raises:
            ParseError: on an unsupported or malformed directive.
        """
        content = cell.lstrip("#").strip()
        if not content.lower().startswith(cls.IMPORT_DIRECTIVE_MARKER):
            # An ordinary comment row, not a Nautobot import directive
            return {}
        content = content[len(cls.IMPORT_DIRECTIVE_MARKER) :].strip()

        directives = {}
        current_key = None
        for segment in (s.strip() for s in content.split(";")):
            if not segment:
                continue
            if "=" in segment:
                key, _, value = segment.partition("=")
                current_key = key.strip().lower()
                if current_key not in cls.SUPPORTED_IMPORT_DIRECTIVES:
                    raise ParseError(
                        f'Unsupported import directive "{current_key}"; '
                        f"supported directives are: {', '.join(cls.SUPPORTED_IMPORT_DIRECTIVES)}"
                    )
                directives[current_key] = [v for v in re.split(r"[\s,]+", value.strip()) if v]
            elif current_key is not None:
                # A continuation of the previous directive's values, e.g. `match_fields=name;serial`
                directives[current_key].extend(v for v in re.split(r"[\s,]+", segment) if v)
            else:
                raise ParseError(f'Malformed import directive "{segment}"; expected "key=value(s)"')

        for key, values in directives.items():
            if not values:
                raise ParseError(f'No value(s) specified for import directive "{key}"')

        return directives

    def _consume_directive_rows(self, reader):
        """
        Consume any leading comment/directive rows from the given csv.reader.

        A row is a comment/directive row if its first *cell* begins with `#`. Checking the first cell, rather
        than the first character of the raw line, is what lets a directive survive a spreadsheet
        open-edit-save cycle, in which the row may come back as a quoted cell.

        Returns:
            (tuple): A `(directives, fieldnames)` tuple - the parsed directives dict, and the header row as a
                list of field names (or None if the file has no header row).
        """
        directives = {}
        for row in reader:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            if row[0].lstrip().startswith("#"):
                directives.update(self.parse_directive_cell(row[0]))
                continue
            return directives, row
        return directives, None

    @staticmethod
    def validate_field_names(field_names, serializer):
        """
        Confirm that every provided field name (or the head of every `__` lookup path) is a serializer field.

        Raises:
            ParseError: naming every unrecognized field, if any.
        """
        heads = {field_name.split("__", 1)[0] for field_name in field_names if field_name}
        unknown = sorted(head for head in heads if not head.startswith("cf_") and head not in serializer.fields)
        if unknown:
            raise ParseError(
                f"Unrecognized field(s) in import data: {', '.join(unknown)}. "
                "Fields must be field names of the serializer for this content-type."
            )

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        serializer = get_serializer_from_parser_context(parser_context)

        try:
            text_buffer = StringIO(read_import_text(stream, parser_context))
            # Consume any leading `#` comment/directive rows before handing off to the DictReader.
            # csv.reader consumes lines from the buffer lazily, so after this the buffer is positioned
            # exactly at the first data row and the DictReader below picks up from there.
            directives, fieldnames = self._consume_directive_rows(csv.reader(text_buffer))
            if directives:
                # Surface the parsed directives to the caller (e.g. the ImportObjects system job) out-of-band;
                # callers that don't care about them (e.g. the REST API) simply ignore this key.
                parser_context.setdefault("import_directives", {}).update(directives)
            if fieldnames is None:
                # The file contained no header row (it was empty, or contained only comments/directives)
                return []
            if parser_context.get("strict_fields"):
                # Fail clearly on unrecognized columns rather than silently ignoring them
                self.validate_field_names(fieldnames, serializer)
            reader = csv.DictReader(text_buffer, fieldnames=fieldnames)

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
            nest_flat_dict({key: value[i] for key, value in flat_data.items()}, CSV_NULL_SENTINELS)
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
        fields_value_mapping = nest_flat_dict(valid_row_data, CSV_NULL_SENTINELS)
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
                    if isinstance(value, str):
                        if value.lstrip().startswith("["):
                            # A JSON-encoded cell containing a list of natural-key dicts,
                            # e.g. `[{"manufacturer__name": "Cisco", "model": "3750"}, ...]`
                            value = json.loads(value)
                        else:
                            # A list of related objects, represented as a list of composite-keys or scalars
                            value = value.split(",")
                    # A dictionary of fields identifying the objects
                    elif isinstance(value, dict):
                        value = self._convert_m2m_dict_to_list_of_dicts(value, key)
                else:
                    value = []
            elif isinstance(serializer_field, serializers.RelatedField):
                # A single related object, represented by its composite-key
                if not value:
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


class ImportDocumentParserMixin:
    """
    Shared logic for the JSON/YAML import parsers.

    Files may be wrapped in a metadata document carrying their own import intent
    (following the `kubectl apply` model):

        nautobot_import: "1"
        model: dcim.device
        match_fields: [name, serial]
        records:
          - name: core-router-01
            ...

    or may be a bare list of records. Document metadata is surfaced to the caller out-of-band via
    `parser_context["import_directives"]` (match_fields) and `parser_context["import_model"]`.
    """

    SUPPORTED_DOCUMENT_VERSIONS = (IMPORT_DOCUMENT_VERSION,)

    def load(self, text):
        """Deserialize the raw text into Python data; implemented per format."""
        raise NotImplementedError

    @classmethod
    def unwrap_document(cls, payload):
        """
        Split a loaded payload into (metadata dict, list of records).

        Raises:
            ParseError: if the payload is neither an document mapping nor a bare list of records.
        """
        if isinstance(payload, dict):
            if IMPORT_DOCUMENT_RECORDS_KEY not in payload:
                raise ParseError(
                    f'Import data is a mapping but has no "{IMPORT_DOCUMENT_RECORDS_KEY}" key; '
                    "expected an import document"
                )
            version = payload.get(IMPORT_DOCUMENT_VERSION_KEY)
            if version is not None and str(version) not in cls.SUPPORTED_DOCUMENT_VERSIONS:
                raise ParseError(f'Unsupported {IMPORT_DOCUMENT_VERSION_KEY} document version "{version}"')
            metadata = {key: value for key, value in payload.items() if key != IMPORT_DOCUMENT_RECORDS_KEY}
            records = payload[IMPORT_DOCUMENT_RECORDS_KEY]
        elif isinstance(payload, list):
            metadata = {}
            records = payload
        else:
            raise ParseError("Import data must be either an import document or a list of records")
        if not isinstance(records, list):
            raise ParseError('The "records" value of an import document must be a list')
        return metadata, records

    def record_to_data(self, counter, record, serializer, strict=True):
        """
        Normalize a single record into a dict suitable for consumption by the serializer.

        Accepts both nested representations (`{"location": {"name": ...}}`) and flat `__` lookups
        (`{"location__name": ...}`); values are already typed, so this is mostly unknown-field
        rejection and `cf_` custom-field normalization.
        """
        if not isinstance(record, dict):
            raise ParseError(f"Record {counter}: expected a mapping of field names to values")
        record = nest_flat_dict(record, CSV_NULL_SENTINELS)
        data = {}
        unknown = []
        for key, value in record.items():
            if key.startswith("cf_"):
                data.setdefault("custom_fields", {})[key[3:]] = value
                continue
            serializer_field = serializer.fields.get(key)
            if serializer_field is None:
                unknown.append(key)
                continue
            if serializer_field.read_only and key != "id":
                continue
            data[key] = value
        if unknown and strict:
            raise ParseError(f"Record {counter}: unrecognized field(s): {', '.join(sorted(unknown))}")
        return data

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        serializer = get_serializer_from_parser_context(parser_context)

        try:
            payload = self.load(read_import_text(stream, parser_context))
            metadata, records = self.unwrap_document(payload)
            if metadata.get(IMPORT_DOCUMENT_MATCH_FIELDS_KEY):
                match_fields = metadata[IMPORT_DOCUMENT_MATCH_FIELDS_KEY]
                if isinstance(match_fields, str):
                    match_fields = match_fields.split()
                parser_context.setdefault("import_directives", {})["match_fields"] = list(match_fields)
            if metadata.get(IMPORT_DOCUMENT_MODEL_KEY):
                parser_context["import_model"] = metadata[IMPORT_DOCUMENT_MODEL_KEY]

            strict = parser_context.get("strict_fields", True)
            return [
                self.record_to_data(counter, record, serializer, strict=strict)
                for counter, record in enumerate(records, start=1)
            ]
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(str(exc)) from exc


class NautobotJSONImportParser(ImportDocumentParserMixin, BaseParser):
    """Bulk-import parser for JSON files, with optional metadata document."""

    media_type = "application/json"

    def load(self, text):
        return json.loads(text)


class NautobotYAMLImportParser(ImportDocumentParserMixin, BaseParser):
    """Bulk-import parser for YAML files, with optional metadata document."""

    media_type = "application/yaml"

    def load(self, text):
        return yaml.safe_load(text)
