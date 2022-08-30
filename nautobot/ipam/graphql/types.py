import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.dcim.graphql.types import InterfaceType
from nautobot.extras.models import DynamicGroup
from nautobot.ipam import models, filters
from nautobot.extras.graphql.types import TagType  # noqa: F401
from nautobot.virtualization.graphql.types import VMInterfaceType


class AggregateType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Aggregate model."""

    prefix = graphene.String()

    class Meta:
        model = models.Aggregate
        filterset_class = filters.AggregateFilterSet


class AssignedObjectType(graphene.Union):
    """GraphQL type object for IPAddress's assigned_object field."""

    class Meta:
        types = (InterfaceType, VMInterfaceType)

    @classmethod
    def resolve_type(cls, instance, info):
        if type(instance).__name__ == "Interface":
            return InterfaceType
        elif type(instance).__name__ == "VMInterface":
            return VMInterfaceType
        return None


class IPAddressType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()
    assigned_object = AssignedObjectType()
    family = graphene.Int()
    interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    vminterface = graphene.Field("nautobot.virtualization.graphql.types.VMInterfaceType")
    nat_outside = graphene.Field(lambda: IPAddressType)
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet

    def resolve_assigned_object(self, args):
        """
        Required by GraphQL query optimizer due to the complex nature of this relationship that
        hinders it from being auto-discovered. The `AssignedObjectType` union will not function
        without this.
        """
        if self.assigned_object:
            return self.assigned_object
        return None

    def resolve_family(self, args):
        return self.family

    def resolve_interface(self, args):
        if self.assigned_object and type(self.assigned_object).__name__ == "Interface":
            return self.assigned_object
        return None

    def resolve_vminterface(self, args):
        if self.assigned_object and type(self.assigned_object).__name__ == "VMInterface":
            return self.assigned_object
        return None

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_objectƒ(self)


class PrefixType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()
    family = graphene.Int()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet

    def resolve_family(self, args):
        return self.family

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)
