import csv
from io import StringIO
import logging
from uuid import UUID

from rest_framework import serializers
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer

from nautobot.core.api.serializers import NautobotHyperlinkedRelatedField
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models import BaseModel
from nautobot.extras.models import CustomField


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

        Unlike other DRF Renderers, `data` should be a dict with key "serializer" (the instantiated serializer for
        this view) and either of the keys "instance" (for a single object) or "queryset" (for a list of objects).
        """
        if not data:
            return ''

        if not isinstance(data, dict) or "serializer" not in data:
            raise ValueError("data should be a dict with the keys 'serializer' and either 'instance' or 'queryset'.")

        objects = data.get("queryset", [data["instance"]])
        serializer = data["serializer"]

        headers = self.get_headers(serializer)

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for obj in objects:
            writer.writerow(self.format_row(obj, headers=headers, serializer=serializer))

        return buffer.getvalue()

    def get_headers(self, serializer):
        """Identify the appropriate CSV headers corresponding to the given serializer."""
        base_headers = list(serializer.fields)
        logger.info("base_headers from %s: %s", type(serializer).__name__, base_headers)

        # Remove specific headers that we know are irrelevant
        for undesired_header in [
            "custom_fields",  # will be handled later as a special case
            "notes_url",
            "tree_depth",
            "url",
            "web_url",  # TODO remove as unnecessary
        ]:
            if undesired_header in base_headers:
                base_headers.remove(undesired_header)
        # Remove all object-count headers
        for header in list(base_headers):
            if header.endswith("_count"):
                base_headers.remove(header)

        if "custom_fields" in serializer.fields:
            cf_keys = CustomField.objects.get_for_model(serializer.Meta.model).values_list("key", flat=True)
            cf_headers = sorted([f"cf_{key}" for key in cf_keys])

        # TODO: relationships? computed fields?

        headers = base_headers + cf_headers

        logger.info("Headers are: %s", headers)
        return headers

    def format_row(self, obj, *, headers, serializer):
        for key in headers:
            if key.startswith("cf_"):
                value = obj._custom_field_data.get(key[3:], None)
            elif isinstance(serializer.fields[key], NautobotHyperlinkedRelatedField):
                # We use this workaround because for a HyperlinkedRelatedField,
                # field.get_attribute(obj) returns only the PK of the object, instead of the entire related object.
                # Calling the superclass get_attribute() gives us the actual related object.
                related_object = serializers.Field.get_attribute(serializer.fields[key], obj)
                try:
                    value = related_object.natural_key()
                except NotImplementedError:
                    logger.error("related_object %s doesn't implement natural_key()", type(related_object).__name__)
                    value = None
            elif key == "tags":
                tags = serializers.Field.get_attribute(serializer.fields[key], obj)
                value = [tag.name for tag in tags.all()]
            else:
                value = serializer.data[key]

            logger.info("Initial value for %s on %s: %s (%s)", key, obj, value, type(value))

            if value is None:
                value = ""
            elif isinstance(value, (list, tuple)):
                value = ",".join([str(v) for v in value])
            else:
                value = str(value)

            logger.info("CSV-compatible value for %s on %s: %s", key, obj, value)

            yield value
