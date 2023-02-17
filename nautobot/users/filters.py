import django_filters
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from nautobot.dcim.models import RackReservation
from nautobot.extras.models import ObjectChange
from nautobot.users.models import ObjectPermission, Token
from nautobot.core.filters import (
    BaseFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)

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
    groups_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group",
    )
    groups = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )
    has_changes = RelatedMembershipBooleanFilter(
        field_name="changes",
        label="Has Changes",
    )
    changes = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="user_name",
        queryset=ObjectChange.objects.all(),
        label="Object Changes (ID or user_name)",
    )
    has_object_permissions = RelatedMembershipBooleanFilter(
        field_name="object_permissions",
        label="Has object permissions",
    )
    object_permissions = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ObjectPermission.objects.all(),
        label="Object Permission (ID or name)",
    )
    has_rack_reservations = RelatedMembershipBooleanFilter(
        field_name="rackreservation",
        label="Has Changes",
    )
    # TODO(timizuo): Since RackReservation has no natural-key field, NaturalKeyOrPKMultipleChoiceFilter can't be used
    rack_reservations_id = django_filters.ModelMultipleChoiceFilter(
        field_name="rackreservation",
        queryset=RackReservation.objects.all(),
        label="Rack Reservation (ID)",
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


class ObjectPermissionFilterSet(BaseFilterSet):
    users = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="users",
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User (ID or username)",
    )
    groups_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group",
    )
    groups = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )

    class Meta:
        model = ObjectPermission
        fields = ["id", "name", "enabled", "object_types", "description"]
