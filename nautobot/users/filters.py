from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from nautobot.core.filters import (
    BaseFilterSet,
    ModelMultipleChoiceFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)
from nautobot.dcim.models import RackReservation
from nautobot.extras.models import ObjectChange
from nautobot.users.models import ObjectPermission, Token

__all__ = (
    "GroupFilterSet",
    "ObjectPermissionFilterSet",
    "UserFilterSet",
)


class GroupFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains"})

    class Meta:
        model = Group
        fields = ["id", "name"]


class UserFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "username": "icontains",
            "first_name": "icontains",
            "last_name": "icontains",
            "email": "icontains",
        },
    )
    # TODO(timizuo): Collapse groups_id and groups into single NaturalKeyOrPKMultipleChoiceFilter; This cant be done now
    #  because Group uses integer as its pk field and NaturalKeyOrPKMultipleChoiceFilter do not properly handle this yet
    groups_id = ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group (ID)",
    )
    groups = ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
    )
    has_object_changes = RelatedMembershipBooleanFilter(
        field_name="object_changes",
        label="Has Changes",
    )
    object_changes = ModelMultipleChoiceFilter(
        field_name="object_changes",
        queryset=ObjectChange.objects.all(),
        label="Object Changes (ID)",
    )
    has_object_permissions = RelatedMembershipBooleanFilter(
        field_name="object_permissions",
        label="Has object permissions",
    )
    object_permissions = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ObjectPermission.objects.all(),
    )
    has_rack_reservations = RelatedMembershipBooleanFilter(
        field_name="rack_reservations",
        label="Has Rack Reservations",
    )
    # TODO(timizuo): Since RackReservation has no natural-key field, NaturalKeyOrPKMultipleChoiceFilter can't be used
    rack_reservations_id = ModelMultipleChoiceFilter(
        field_name="rack_reservations",
        queryset=RackReservation.objects.all(),
    )

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
        ]


class TokenFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"description": "icontains"})

    class Meta:
        model = Token
        fields = ["id", "key", "write_enabled", "created", "expires", "description"]


class ObjectPermissionFilterSet(BaseFilterSet, NameSearchFilterSet):
    users = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=get_user_model().objects.all(),
        to_field_name="username",
    )
    # TODO(timizuo): Collapse groups_id and groups into single NaturalKeyOrPKMultipleChoiceFilter; This cant be done now
    #  because Group uses integer as its pk field and NaturalKeyOrPKMultipleChoiceFilter do not properly handle this yet
    groups_id = ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group (ID)",
    )
    groups = ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )

    class Meta:
        model = ObjectPermission
        fields = ["id", "name", "enabled", "object_types", "description"]
