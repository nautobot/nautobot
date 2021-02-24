import graphene
from django.db.models import JSONField
from django.db.models.fields import BinaryField

from graphene.types import generic
from graphene_django.converter import convert_django_field


@convert_django_field.register(JSONField)
def convert_field_to_string(field, registry=None):
    """Convert JSONField to GenericScalar."""
    return generic.GenericScalar()


@convert_django_field.register(BinaryField)
def convert_field_to_string(field, registry=None):  # noqa: F811
    """Convert BinaryField to String."""
    return graphene.String()
