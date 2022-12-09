from django.contrib.contenttypes.models import ContentType

import graphene_django_optimizer as gql_optimizer

from nautobot.core import models, filters


class ContentTypeType(gql_optimizer.OptimizedDjangoObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType


class DynamicGroupType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type object for `DynamicGroup` model."""

    class Meta:
        model = models.DynamicGroup
        filterset_class = filters.DynamicGroupFilterSet
