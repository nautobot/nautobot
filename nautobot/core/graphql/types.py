from django.contrib.contenttypes.models import ContentType
import graphene
import graphene_django_optimizer as gql_optimizer


class OptimizedNautobotObjectType(gql_optimizer.OptimizedDjangoObjectType):
    url = graphene.String()

    def resolve_url(self, info):
        return self.get_absolute_url(api=True)

    class Meta:
        abstract = True


class ContentTypeType(OptimizedNautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType
