from django.contrib.contenttypes.models import ContentType

from .base import NautobotObjectType


class ContentTypeType(NautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType
