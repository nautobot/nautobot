import csv
from io import StringIO
import json
import logging

from django.conf import settings
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models.constants import COMPOSITE_KEY_SEPARATOR


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

        headers = self.get_headers(data)

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for record in data:
            writer.writerow(
                self.object_to_row_elements(
                    record,
                    headers=headers,
                )
            )

        return buffer.getvalue()

    @classmethod
    def get_headers(cls, data):
        """Identify the appropriate CSV headers corresponding to the given data."""
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

        # TODO: relationships? computed fields?

        headers = base_headers + cf_headers

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
                else:
                    value = json.dumps(value)
            elif isinstance(value, (list, tuple, set)):
                if isinstance(value, set):
                    value = sorted(value)
                if value and isinstance(value[0], dict) and "composite_key" in value[0]:
                    # Multiple nested related objects
                    if value[0].get("generic_foreign_key"):
                        # Multiple *generic* nested related obects
                        value = [COMPOSITE_KEY_SEPARATOR.join([v["object_type"], v["composite_key"]]) for v in value]
                    else:
                        value = [v["composite_key"] for v in value]
                # The below makes for better UX than `json.dump()` for most current cases.
                value = ",".join([str(v) if v is not None else "" for v in value])
            elif not isinstance(value, (str, int)):
                value = str(value)

            if settings.DEBUG:
                logger.debug("key: %s, value: %s", key, value)
            yield value
