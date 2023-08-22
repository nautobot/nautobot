from django.contrib.contenttypes.models import ContentType
from rest_framework.reverse import NoReverseMatch, reverse
import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.utilities.utils import get_route_for_model


class OptimizedNautobotObjectType(gql_optimizer.OptimizedDjangoObjectType):
    url = graphene.String()

    def resolve_url(self, info):
        for action in ["retrieve", "detail", ""]:
            route = get_route_for_model(self._meta.model, action, api=True)

            for field in ["pk", "slug"]:
                try:
                    return reverse(route, kwargs={field: getattr(self, field)}, request=info.context)
                except (NoReverseMatch, AttributeError):
                    continue

        return None

    class Meta:
        abstract = True


class ContentTypeType(OptimizedNautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType
