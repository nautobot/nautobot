import csv
from io import StringIO
import json
import logging

from django.conf import settings
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.constants import COMPOSITE_KEY_SEPARATOR

logger = logging.getLogger(__name__)


class FormlessBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    Override the built-in BrowsableAPIRenderer to disable HTML forms.
    """

    def show_form_for_method(self, view, method, request, obj):
        """Returns True if a form should be shown for this method."""
        if method == "OPTIONS":
            return super().show_form_for_method(view, method, request, obj)
        return False

    def get_filter_form(self, data, view, request):
        return None


class NautobotJSONRenderer(JSONRenderer):
    """
    Override the encoder_class of the default JSONRenderer to handle the rendering of TagsManager in Nautobot API.
    """

    encoder_class = NautobotKombuJSONEncoder


def join_list_cell(values):
    """Join a list of values into a single comma-separated CSV cell.

    Members are quoted by CSV's own rules, so a member containing a comma, quote or newline stays distinct
    from two members and `a,b` renders exactly as it always did. Inverse of `NautobotCSVParser.split_list_cell`.
    """
    buffer = StringIO()
    csv.writer(buffer, lineterminator="").writerow(values)
    return buffer.getvalue()


class NautobotCSVRenderer(BaseRenderer):
    """
    Render to CSV format.

    Loosely inspired by https://github.com/mjumbewu/django-rest-framework-csv/.
    """

    media_type = "text/csv"
    format = "csv"
    charset = "UTF-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render the provided data to CSV format.
        """
        if not data:
            return ""

        # TODO need to handle rendering of exceptions (e.g. not authenticated) as those have a different data dict.
        if isinstance(data, dict):
            data = [data]

        headers = self.get_headers(data, field_order=(renderer_context or {}).get("field_order"))

        buffer = StringIO()
        writer = csv.writer(buffer)
        import_directives = (renderer_context or {}).get("import_directives")
        if import_directives:
            self.render_directive_row(writer, import_directives)
        writer.writerow(headers)
        for record in data:
            writer.writerow(
                self.object_to_row_elements(
                    record,
                    headers=headers,
                )
            )

        return buffer.getvalue()

    def render_directive_row(self, writer, directives):
        """
        Render `build_import_metadata` as a leading `# nautobot_import_version=1; ...` row.

        The version directive doubles as the marker identifying the row as Nautobot's. The directive occupies
        a single cell so it survives spreadsheet open-edit-save cycles; see the matching first-cell parsing
        in NautobotCSVParser.
        """
        entries = []
        for key, value in directives.items():
            if isinstance(value, (list, tuple)):
                value = " ".join(str(v) for v in value)
            entries.append(f"{key}={value}")
        writer.writerow([f"# {'; '.join(entries)}"])

    @classmethod
    def get_headers(cls, data, field_order=None):
        """
        Identify the appropriate CSV headers corresponding to the given data.

        If `field_order` (a list of field names / `__` lookup paths, e.g. from an explicit export field
        selection) is given, headers are ordered to match it instead of the default priority ordering, and
        the `cf_*` headers are restricted to the custom fields it names.
        """
        base_headers = list(data[0].keys())

        # Remove specific headers that we know are irrelevant
        for undesired_header in [
            "computed_fields",
            "custom_fields",  # will be handled later as a special case
            "notes_url",  # irrelevant to CSV
            "relationships",
            "url",  # irrelevant to CSV
        ]:
            if undesired_header in base_headers:
                base_headers.remove(undesired_header)

        # Add individual headers for each relevant custom field
        # Since we know there are cases where custom field data may be missing from a given instance,
        # we iterate over *all* instances in the data set to be safe.
        if "custom_fields" in data[0]:
            cf_headers = set()
            for record in data:
                cf_headers |= {f"cf_{key}" for key in record["custom_fields"]}
            cf_headers = sorted(cf_headers)
        else:
            cf_headers = []

        # These headers come from the data rather than from the serializer's field set, so an explicit
        # selection has to be applied to them here -- `OptInFieldsMixin` can only narrow the field set down
        # to `custom_fields` as a whole, and every custom field of the object is inside it. Naming
        # `custom_fields` asks for all of them; otherwise only the `cf_<key>` entries actually selected.
        if field_order and "custom_fields" not in field_order:
            selected_cf_headers = {entry for entry in field_order if entry.startswith("cf_")}
            cf_headers = [header for header in cf_headers if header in selected_cf_headers]

        # TODO: relationships? computed fields?

        headers = base_headers + cf_headers

        if field_order:
            # Order headers to match the explicit field selection; a header belongs to the earliest
            # selection entry it equals or nests under (e.g. `location__name` under `location`).
            def selection_index(header):
                for index, selected in enumerate(field_order):
                    if header == selected or header.startswith(f"{selected}__"):
                        return (index, header)
                return (len(field_order), header)

            headers.sort(key=selection_index)
        else:
            # Coerce important fields, if present, to the front of the list
            for priority_header in ["id", "composite_key", "display", "name"]:
                if priority_header in headers:
                    headers.remove(priority_header)
                    headers.insert(0, priority_header)

        return headers

    def object_to_row_elements(self, record, *, headers):
        """Given an object and the desired CSV headers, yield the serialized values for each header."""
        for key in headers:
            # Retrieve the base value corresponding to this key
            if key.startswith("cf_"):
                # Custom field
                value = record.get("custom_fields", {}).get(key[3:], None)
            else:
                value = record.get(key)

            # Coerce the value to a format to make the CSV renderer happy (i.e. a string or number)
            if value is None:
                # Unfortunately we're going to have to be a bit lossy here, as CSV doesn't have a distinction between
                # a null value and an empty string value for a column.
                # We could choose to represent a null value as "None" or "null" but those are also valid strings, so...
                # See corresponding logic in NautobotCSVParser.
                value = ""
            elif isinstance(value, dict):
                if "composite_key" in value:
                    # A nested related object
                    if value.get("generic_foreign_key"):
                        # A *generic* nested related object
                        value = COMPOSITE_KEY_SEPARATOR.join([value["object_type"], value["composite_key"]])
                    else:
                        value = value["composite_key"]
                elif "value" in value and "label" in value:
                    # An enum type
                    value = value["value"]
                elif "id" in value:
                    value = str(value["id"])
                else:
                    value = json.dumps(value)
            elif isinstance(value, (list, tuple, set)):
                if isinstance(value, set):
                    value = sorted(value)
                if value and isinstance(value[0], dict) and ("id" in value[0]):
                    # TODO: Potentially reintroduce "composite_key" above? ` or "composite_key" in value[0]`
                    # Multiple nested related objects
                    if value[0].get("generic_foreign_key"):
                        # Multiple *generic* nested related obects
                        value = [COMPOSITE_KEY_SEPARATOR.join([v["object_type"], v["composite_key"]]) for v in value]
                    # elif value[0].get("composite_key"):  # TODO: Potentially reintroduce "composite_key"?
                    #     value = [v["composite_key"] for v in value]
                    else:
                        value = [v["id"] for v in value]
                if value and isinstance(value[0], dict) and ("value" in value[0]) and ("label" in value[0]):
                    # Multiple enum types
                    value = [v["value"] for v in value]
                if value and isinstance(value[0], dict):
                    # Generic list-of-dicts (e.g. a JSONField containing structured data such as
                    # `CableType.mapping`) — render as JSON so the CSV → POST round-trip via the
                    # parser's `json.loads` produces an identical list. The comma-of-reprs
                    # fallback below would emit Python repr (single quotes), which doesn't parse.
                    value = json.dumps(value)
                else:
                    # The below makes for better UX than `json.dump()` for most current cases.
                    value = join_list_cell([str(v) if v is not None else "" for v in value])
            elif not isinstance(value, (str, int)):
                value = str(value)

            if settings.DEBUG:
                logger.debug("key: %s, value: %s", key, value)
            yield value
