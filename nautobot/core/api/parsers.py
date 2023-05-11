import csv
import codecs
from io import StringIO
import json
import logging

from rest_framework import serializers
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
            serializer_class = parser_context["view"].serializer_class
        except (KeyError, AttributeError):
            logger.error("Unable to find serializer_class for the view?")
            return None

        serializer = serializer_class(context={"request": parser_context.get("request", None)})

        text = stream.read().decode(encoding)
        logger.info(text)
        reader = csv.DictReader(StringIO(text))
        data = []
        for row in reader:
            data.append(self.row_elements_to_data(row, serializer=serializer))

        # TODO should we have a smarter way to distinguish between single-object and bulk operations?
        if len(data) == 1:
            data = data[0]

        # logger.info("data: %s", json.dumps(data, indent=2))
        return data

    def row_elements_to_data(self, row, serializer):
        """
        Parse a single row of CSV data (represented as a dict) into a dict suitable for consumption by the serializer.

        TODO: it would be more elegant if our serializer fields knew how to deserialize the CSV data themselves;
        we could then literally have the parser just return list(reader) and not need this function at all.
        """
        data = {}
        for key, value in row.items():
            serializer_field = serializer.fields.get(key, None)

            if key.startswith("cf_"):
                # Custom field
                data.setdefault("custom_fields", {})[key[3:]] = value
                continue

            # logger.info("%s: %s", key, serializer_field)

            if serializer_field.read_only:
                continue

            if isinstance(serializer_field, serializers.ManyRelatedField):
                # A list of related objects, represented as a list of natural-key-slugs
                if value:
                    related_model = serializer_field.child_relation.queryset.model
                    value = [self.get_natural_key_dict(slug, related_model) for slug in value.split(",")]
            elif isinstance(serializer_field, serializers.RelatedField):
                # A single related object, represented by its natural key
                if value:
                    related_model = serializer_field.queryset.model
                    value = self.get_natural_key_dict(value, related_model)
            elif isinstance(serializer_field, serializers.JSONField):
                value = json.loads(value)

            if value == "" and serializer_field.allow_null:
                value = None

            # logger.info("%s: %s", key, value)
            data[key] = value

        return data

    def get_natural_key_dict(self, natural_key_or_slug, model):
        """
        Get the data dictionary corresponding to the given natural key list or natural-key-slug for the given model.
        """
        if not natural_key_or_slug:
            return None
        if isinstance(natural_key_or_slug, (list, tuple)):
            natural_key = natural_key_or_slug
        elif model._meta.label_lower == "contenttypes.contenttype":
            natural_key = natural_key_or_slug.split(".")
        else:
            natural_key = deconstruct_natural_key_slug(natural_key_or_slug)

        if model._meta.label_lower == "contenttypes.contenttype":
            return {"app_label": natural_key[0], "model": natural_key[1]}
        elif model._meta.label_lower == "auth.group":
            return {"name": natural_key[0]}

        try:
            return model.natural_key_args_to_kwargs(natural_key)
        except AttributeError:
            logger.error("%s doesn't implement natural_key_field_args_to_kwargs()", model.__name__)
            return {"pk": natural_key[0]}
