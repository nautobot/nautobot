from django.contrib.contenttypes.models import ContentType

import graphene_django_optimizer as gql_optimizer


class ContentTypeType(gql_optimizer.OptimizedDjangoObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType
