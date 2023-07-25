from django.contrib.contenttypes.models import ContentType

from nautobot.extras.graphql.types import OptimizedNautobotObjectType


class ContentTypeType(OptimizedNautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType
