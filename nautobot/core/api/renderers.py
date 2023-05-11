import csv
from io import StringIO
import json
import logging

from django.conf import settings
from rest_framework import serializers
from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models.constants import NATURAL_KEY_SLUG_SEPARATOR
from nautobot.core.models.utils import construct_natural_key_slug
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

        Unlike other DRF Renderers, `data` should be a dict with key "serializer_class" (the serializer for
        this view) and either of the keys "instance" (for a single object) or "queryset" (for a list of objects).
        """
        if not data:
            return ""

        if not isinstance(data, dict) or "serializer_class" not in data:
            raise ValueError(
                "data should be a dict with the keys 'serializer_class' and either 'instance' or 'queryset'."
            )

        serializer_class = data["serializer_class"]
        objects = data.get("queryset", [data.get("instance")])
        if not objects:
            return ""

        headers = self.get_headers(serializer_class(objects[0], context={"request": renderer_context["request"]}))

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for obj in objects:
            writer.writerow(
                self.object_to_row_elements(
                    obj,
                    headers=headers,
                    serializer=serializer_class(obj, context={"request": renderer_context["request"]}),
                )
            )

        return buffer.getvalue()

    @classmethod
    def get_headers(cls, serializer):
        """Identify the appropriate CSV headers corresponding to the given serializer."""
        base_headers = list(serializer.fields)

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

        # Remove any write-only fields as we won't have values for those fields on read
        for header in list(base_headers):
            if serializer.fields[header].write_only:
                base_headers.remove(header)

        # Add individual headers for each relevant custom field
        if "custom_fields" in serializer.fields:
            cf_keys = CustomField.objects.get_for_model(serializer.Meta.model).values_list("key", flat=True)
            cf_headers = sorted([f"cf_{key}" for key in cf_keys])
        else:
            cf_headers = []

        # TODO: relationships? computed fields?

        headers = base_headers + cf_headers

        # Coerce important fields, if present, to the front of the list
        for priority_header in ["id", "natural_key_slug", "display", "name"]:
            if priority_header in headers:
                headers.remove(priority_header)
                headers.insert(0, priority_header)

        if settings.DEBUG:
            logger.debug("CSV headers for %s are: %s", type(serializer).__name__, headers)
        return headers

    def object_to_row_elements(self, obj, *, headers, serializer):
        """Given an object, the desired CSV headers, and its serializer, yield the serialized values for each header."""
        for key in headers:
            serializer_field = serializer.fields.get(key, None)

            # Retrieve the base value corresponding to this key
            if key.startswith("cf_"):
                # Custom field
                value = obj._custom_field_data.get(key[3:], None)
            elif isinstance(serializer_field, serializers.ListSerializer):
                # A list of related objects - use the natural key slug for each such object
                related_queryset = serializer_field.get_attribute(obj)
                value = [self.get_natural_key_slug(related_object) for related_object in related_queryset.all()]
            elif isinstance(serializer_field, serializers.Serializer):
                # A single related object - use its natural key slug
                related_object = serializer_field.get_attribute(obj)
                value = self.get_natural_key_slug(related_object)
            else:
                # Default case - start with the REST API serializer representation
                value = serializer.data[key]

            # Coerce the value to a format to make the CSV renderer happy (i.e. a string or number)
            if value is None:
                # Unfortunately we're going to have to be a bit lossy here, as CSV doesn't have a distinction between
                # a null value and an empty string value for a column.
                # We could choose to represent a null value as "None" or "null" but those are also valid strings, so...
                value = ""
            elif isinstance(value, dict):
                if "id" in value and "object_type" in value:
                    # A related object from a polymorphic serializer that we weren't able to catch above?
                    # Serialize it as if it were a GenericForeignKey
                    value = NATURAL_KEY_SLUG_SEPARATOR.join([value["object_type"], value["natural_key_slug"]])
                elif "value" in value and "label" in value:
                    # An enum type
                    value = value["value"]
                else:
                    value = json.dumps(value)
            elif isinstance(value, (list, tuple)):
                if value and isinstance(value[0], dict) and "id" in value[0] and "object_type" in value[0]:
                    # Multiple related objects - serialize them as GenericForeignKeys
                    value = [NATURAL_KEY_SLUG_SEPARATOR.join([v["object_type"], v["natural_key_slug"]]) for v in value]
                value = ",".join([str(v) if v is not None else "" for v in value])
            elif not isinstance(value, (str, int)):
                value = str(value)

            if settings.DEBUG:
                logger.debug("key: %s, value: %s", key, value)
            yield value

    def get_natural_key_slug(self, obj):
        """Get the natural key slug for the given object, if any."""
        if obj is None:
            return None

        # Match ContentTypeField representation for ContentType objects
        if obj._meta.label_lower == "contenttypes.contenttype":
            return f"{obj.app_label}.{obj.model}"

        try:
            return construct_natural_key_slug(obj.natural_key())
        except (NotImplementedError, AttributeError):
            logger.error("%s doesn't implement natural_key()", type(obj).__name__)
            return str(obj.pk)
