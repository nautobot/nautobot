import csv
from io import StringIO
import logging
from uuid import UUID

from rest_framework.renderers import BaseRenderer, BrowsableAPIRenderer, JSONRenderer

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models import BaseModel


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
            return ''

        logger.info("renderer_context: %s", renderer_context)
        view = renderer_context.get("view", None)
        queryset = getattr(view, "queryset", None)
        logger.info("queryset: %s", queryset)
        serializer_class = getattr(view, "serializer_class", None)

        if isinstance(data, dict) and "results" in data and "next" in data and "previous" in data:
            # TODO: currently list data is wrapped by nautobot.core.api.pagination.OptionalLimitOffsetPagination.
            #       We **probably** want to use a different (or none) paginator for CSV export?
            #       Might be feasible by replacing `data` with a data set generated from renderer_context["view"]?
            data = data.get("results", [])
        elif not isinstance(data, (list, tuple)):
            # Single object being serialized
            data = [data]

        headers = self.get_headers(data)

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in data:
            writer.writerow(self.format_row(row, headers=headers, queryset=queryset, serializer_class=serializer_class))

        return buffer.getvalue()

    def get_headers(self, data):
        """Identify the appropriate CSV headers for this data."""
        base_headers = list(data[0].keys())

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

        # Add headers for each custom field. We check all rows in `data` in case some objects are missing a field.
        cf_headers = set()
        for row in data:
            cf_headers.update([f"cf_{key}" for key in row.get("custom_fields", {})])

        # TODO: relationships? computed fields?

        headers = base_headers + sorted(cf_headers)

        logger.info("Headers are: %s", headers)
        return headers

    def format_row(self, row, *, headers, queryset, serializer_class):
        for key in headers:
            if key.startswith("cf_"):
                value = row.get("custom_fields", {}).get(key[3:], None)
            else:
                value = row[key]

            if isinstance(value, UUID):
                try:
                    related_model = getattr(queryset.model, key)
                    logger.info("related_model: %s", related_model)
                    value = related_model.objects.get(value).natural_key()
                except:
                    pass

            if value is None:
                value = ""
            elif isinstance(value, (list, tuple)):
                value = ",".join([str(v) for v in value])
            else:
                value = str(value)

            logger.info("value for %s : %s", key, value)

            yield value
