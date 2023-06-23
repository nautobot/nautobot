import json

from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.base import (
    DEFER_FIELD,
    DeserializationError,
    DeserializedObject,
    M2MDeserializationError,
    build_instance,
    deserialize_fk_value,
    deserialize_m2m_values,
)
from django.core.serializers.json import Serializer as JSONSerializer
from django.core.serializers.python import _get_model
from django.db import DEFAULT_DB_ALIAS, models


class Serializer(JSONSerializer):
    """
    Custom Serializer implementation with special handling for GenericForeignKey fields.

    Heavily inspired by
    https://stackoverflow.com/questions/11159377/is-it-possible-to-use-a-natural-key-for-a-genericforeignkey-in-django
    """

    def get_dump_object(self, obj):
        """
        Called from self.end_object() to return the following basic structure for the serialized object:

        {
          "model": "dcim.interface",
          "pk": "035ea413-189b-4ea5-b48c-7b5581775f53",
          "fields": {
            "device": "b5d89641-668d-4b6a-8a71-a0396cff1606",
            "name": "Ethernet1/8",
            ...
          }
        }

        In the base Django JSON Serializer, "fields" is populated directly from `self._current`, which has been built
        field-by-field from obj via the `handle_field()`, `handle_fk_field()`, and `handle_m2m_field()` methods.

        GenericForeignKeys are skipped over in the base serializer since they're not in `model._meta.local_fields` or
        in `model._meta.local_many_to_many`, so we need to handle them here as a special case, which will look like:

        {
          "model": "dcim.cablepath",
          "fields": {
            "origin": {
              "model": "circuits.circuittermination",
              "natural_key": [
                "NTT",
                "ntt-92882225616484969",
                "A"
              ]
            },
            ...
          }
        }
        """
        data = super().get_dump_object(obj)
        for field in obj._meta.get_fields():
            if not self.use_natural_foreign_keys or type(field) != GenericForeignKey:
                continue
            related_obj = getattr(obj, field.name)
            if related_obj is not None:
                # Add a new fields entry describing the related obj
                data["fields"][field.name] = {"model": related_obj._meta.label_lower}
                if hasattr(related_obj, "natural_key"):
                    data["fields"][field.name]["natural_key"] = related_obj.natural_key()
                else:
                    data["fields"][field.name]["pk"] = related_obj.pk
                # And delete as redundant the fields describing the components of the GenericForeignKey
                del data["fields"][field.ct_field]
                del data["fields"][field.fk_field]

        return data


def deserialize_gfk_value(field, field_value, using, handle_forward_references):
    """Custom function equivalent to Djangos' deserialize_fk_value() and deserialize_m2m_values() functions."""
    if field_value is None:
        return None, None
    model = _get_model(field_value["model"])
    ct = ContentType.objects.get_for_model(model)
    default_manager = model._default_manager
    try:
        if "natural_key" in field_value and hasattr(default_manager, "get_by_natural_key"):
            obj = default_manager.db_manager(using).get_by_natural_key(*field_value["natural_key"])
        else:
            obj = default_manager.db_manager(using).get(pk=field_value["pk"])
        return ct, obj
    except ObjectDoesNotExist:
        if handle_forward_references:
            return ct, DEFER_FIELD
        else:
            raise


def Deserializer(stream_or_string, **options):
    """
    Custom Deserializer implementation with support for GenericForeignKey fields.

    Heavily inspired by
    https://stackoverflow.com/questions/11159377/is-it-possible-to-use-a-natural-key-for-a-genericforeignkey-in-django
    """
    using = options.get("using", DEFAULT_DB_ALIAS)
    handle_forward_references = options.get("handle_forward_references", False)
    ignorenonexistent = options.get("ignorenonexistent", False)
    field_names_cache = {}
    # code taken from JSONDeserializer
    if not isinstance(stream_or_string, (bytes, str)):
        stream_or_string = stream_or_string.read()
    if isinstance(stream_or_string, bytes):
        stream_or_string = stream_or_string.decode()
    try:
        object_list = json.loads(stream_or_string)
        # code taken from PythonDeserializer
        for d in object_list:
            try:
                model = _get_model(d["model"])
            except DeserializationError:
                if ignorenonexistent:
                    continue
                else:
                    raise
            data = {}
            if "pk" in d:
                try:
                    data[model._meta.pk.attname] = model._meta.pk.to_python(d.get("pk"))
                except Exception as exc:
                    raise DeserializationError.WithData(exc, d["model"], d["pk"], None)

            m2m_data = {}
            deferred_fields = {}

            if model not in field_names_cache:
                field_names_cache[model] = {f.name for f in model._meta.get_fields()}
            field_names = field_names_cache[model]

            for field_name, field_value in d["fields"].items():
                if ignorenonexistent and field_name not in field_names:
                    continue

                field = model._meta.get_field(field_name)

                if field.remote_field and isinstance(field.remote_field, models.ManyToManyRel):
                    # M2M relation
                    try:
                        values = deserialize_m2m_values(field, field_value, using, handle_forward_references)
                    except M2MDeserializationError as exc:
                        raise DeserializationError.WithData(exc.original_exc, d["model"], d.get("pk"), exc.pk)
                    if values == DEFER_FIELD:
                        deferred_fields[field] = field_value
                    else:
                        m2m_data[field.name] = values
                elif field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
                    # FK field
                    try:
                        value = deserialize_fk_value(field, field_value, using, handle_forward_references)
                    except Exception as exc:
                        raise DeserializationError.WithData(exc, d["model"], d.get("pk"), field_value)
                    if value == DEFER_FIELD:
                        deferred_fields[field] = field_value
                    else:
                        data[field.attname] = value
                # BEGIN CUSTOM CODE
                elif type(field) == GenericForeignKey:
                    related_ct, related_obj = deserialize_gfk_value(
                        field, field_value, using, handle_forward_references
                    )
                    data[field.ct_field] = related_ct
                    if related_obj == DEFER_FIELD:
                        deferred_fields[model._meta.get_field(field.fk_field)] = field_value.get(
                            "natural_key", field_value.get("pk")
                        )
                    else:
                        data[field.fk_field] = related_obj.pk
                # END CUSTOM CODE
                else:
                    # Handle all other fields
                    try:
                        data[field.name] = field.to_python(field_value)
                    except Exception as exc:
                        raise DeserializationError.WithData(exc, d["model"], d.get("pk"), field_value)

            obj = build_instance(model, data, using)
            yield DeserializedObject(obj, m2m_data, deferred_fields)
    except (GeneratorExit, DeserializationError):
        raise
    except Exception as exc:
        raise DeserializationError() from exc
