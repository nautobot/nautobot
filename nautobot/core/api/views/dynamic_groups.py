from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from nautobot.core import filters
from nautobot.core.api.serializers.dynamic_groups import DynamicGroupSerializer, DynamicGroupMembershipSerializer
from nautobot.core.api.views import ModelViewSet
from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership
from nautobot.extras.api.views import NotesViewSetMixin
from nautobot.utilities.api import get_serializer_for_model

#
# Dynamic Groups
#


class DynamicGroupViewSet(ModelViewSet, NotesViewSetMixin):
    """
    Manage Dynamic Groups through DELETE, GET, POST, PUT, and PATCH requests.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DynamicGroup.objects.prefetch_related("content_type")
    serializer_class = DynamicGroupSerializer
    filterset_class = filters.DynamicGroupFilterSet

    # FIXME(jathan): Figure out how to do dynamic `responses` serializer based on the `content_type`
    # of the DynamicGroup? May not be possible or even desirable to have a "dynamic schema".
    # @extend_schema(methods=["get"], responses={200: member_response})
    @action(detail=True, methods=["get"])
    def members(self, request, pk, *args, **kwargs):
        """List member objects of the same type as the `content_type` for this dynamic group."""
        instance = get_object_or_404(self.queryset, pk=pk)

        # Retrieve the serializer for the content_type and paginate the results
        member_model_class = instance.content_type.model_class()
        member_serializer_class = get_serializer_for_model(member_model_class)
        members = self.paginate_queryset(instance.members)
        member_serializer = member_serializer_class(members, many=True, context={"request": request})
        return self.get_paginated_response(member_serializer.data)


class DynamicGroupMembershipViewSet(ModelViewSet):
    """
    Manage Dynamic Group Memberships through DELETE, GET, POST, PUT, and PATCH requests.
    """

    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = DynamicGroupMembership.objects.prefetch_related("group", "parent_group")
    serializer_class = DynamicGroupMembershipSerializer
    filterset_class = filters.DynamicGroupMembershipFilterSet
